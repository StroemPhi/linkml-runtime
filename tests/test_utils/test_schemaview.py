import os
import unittest
import logging
from copy import copy

from linkml_runtime.linkml_model.meta import SchemaDefinition, ClassDefinition, SlotDefinitionName, SlotDefinition
from linkml_runtime.loaders.yaml_loader import YAMLLoader
from linkml_runtime.utils.introspection import package_schemaview, object_class_definition
from linkml_runtime.utils.schemaview import SchemaView, SchemaUsage
from linkml_runtime.utils.schemaops import roll_up, roll_down
from tests.test_utils import INPUT_DIR

SCHEMA_NO_IMPORTS = os.path.join(INPUT_DIR, 'kitchen_sink_noimports.yaml')
SCHEMA_WITH_IMPORTS = os.path.join(INPUT_DIR, 'kitchen_sink.yaml')

yaml_loader = YAMLLoader()


class SchemaViewTestCase(unittest.TestCase):

    def test_schemaview(self):
        # no import schema
        view = SchemaView(SCHEMA_NO_IMPORTS)
        logging.debug(view.imports_closure())
        assert len(view.imports_closure()) == 1
        all_cls = view.all_classes()
        logging.debug(f'n_cls = {len(all_cls)}')

        assert list(view.annotation_dict('is current').values()) == ['bar']
        logging.debug(view.annotation_dict('employed at'))
        e = view.get_element('employed at')
        logging.debug(e.annotations)
        e = view.get_element('has employment history')
        logging.debug(e.annotations)

        elements = view.get_elements_applicable_by_identifier("ORCID:1234")
        assert "Person" in elements
        elements = view.get_elements_applicable_by_identifier("PMID:1234")
        assert "Organization" in elements
        elements = view.get_elements_applicable_by_identifier("http://www.ncbi.nlm.nih.gov/pubmed/1234")
        assert "Organization" in elements
        elements = view.get_elements_applicable_by_identifier("TEST:1234")
        assert "anatomical entity" not in elements
        assert list(view.annotation_dict(SlotDefinitionName('is current')).values()) == ['bar']
        logging.debug(view.annotation_dict(SlotDefinitionName('employed at')))
        element = view.get_element(SlotDefinitionName('employed at'))
        logging.debug(element.annotations)
        element = view.get_element(SlotDefinitionName('has employment history'))
        logging.debug(element.annotations)

        assert view.is_mixin('WithLocation')
        assert not view.is_mixin('BirthEvent')

        assert view.inverse('employment history of') == 'has employment history'
        assert view.inverse('has employment history') == 'employment history of'
        
        mapping = view.get_mapping_index()
        assert mapping is not None

        category_mapping = view.get_element_by_mapping("GO:0005198")
        assert category_mapping == ['activity']

        if True:
            for sn, s in view.all_slots().items():
                logging.info(f'SN = {sn} RANGE={s.range}')
            # this section is mostly for debugging
            for cn in all_cls.keys():
                logging.debug(f'{cn} FROM SCHEMA = {view.get_class(cn).from_schema}')
                logging.debug(f'{cn} PARENTS = {view.class_parents(cn)}')
                logging.debug(f'{cn} ANCS = {view.class_ancestors(cn)}')
                logging.debug(f'{cn} CHILDREN = {view.class_children(cn)}')
                logging.debug(f'{cn} DESCS = {view.class_descendants(cn)}')
                logging.debug(f'{cn} SCHEMA = {view.in_schema(cn)}')
                logging.debug(f'  SLOTS = {view.class_slots(cn)}')
                for sn in view.class_slots(cn):
                    slot = view.get_slot(sn)
                    if slot is None:
                        logging.debug(f'NO SLOT: {sn}')
                    else:
                        logging.debug(f'  SLOT {sn} R: {slot.range} U: {view.get_uri(sn)} ANCS: {view.slot_ancestors(sn)}')
                    induced_slot = view.induced_slot(sn, cn)
                    logging.debug(f'    INDUCED {sn}={induced_slot}')

        logging.debug(f'ALL = {view.all_elements().keys()}')

        # -- TEST ANCESTOR/DESCENDANTS FUNCTIONS --

        self.assertCountEqual(['Company', 'Organization', 'HasAliases', 'Thing'],
                              view.class_ancestors('Company'))
        self.assertCountEqual(['Organization', 'HasAliases', 'Thing'],
                              view.class_ancestors('Company', reflexive=False))
        self.assertCountEqual(['Thing', 'Person', 'Organization', 'Company', 'Adult'],
                              view.class_descendants('Thing'))

        # -- TEST CLASS SLOTS --

        self.assertCountEqual(['id', 'name',  ## From Thing
                               'has employment history', 'has familial relationships', 'has medical history',
                               'age in years', 'addresses', 'has birth event', ## From Person
                               'aliases'  ## From HasAliases
                                ],
                              view.class_slots('Person'))
        self.assertCountEqual(view.class_slots('Person'), view.class_slots('Adult'))
        self.assertCountEqual(['id', 'name',  ## From Thing
                               'ceo', ## From Company
                               'aliases'  ## From HasAliases
                               ],
                              view.class_slots('Company'))

        assert view.get_class('agent').class_uri == 'prov:Agent'
        assert view.get_uri('agent') == 'prov:Agent'
        logging.debug(view.get_class('Company').class_uri)

        assert view.get_uri('Company') == 'ks:Company'

        # test induced slots

        for c in ['Company', 'Person', 'Organization',]:
            islot = view.induced_slot('aliases', c)
            assert islot.multivalued is True
            self.assertEqual(islot.owner, c, 'owner does not match')
            self.assertEqual(view.get_uri(islot, expand=True), 'https://w3id.org/linkml/tests/kitchen_sink/aliases')

        assert view.get_identifier_slot('Company').name == 'id'
        assert view.get_identifier_slot('Thing').name == 'id'
        assert view.get_identifier_slot('FamilialRelationship') is None
        for c in ['Company', 'Person', 'Organization', 'Thing']:
            assert view.induced_slot('id', c).identifier is True
            assert view.induced_slot('name', c).identifier is not True
            assert view.induced_slot('name', c).required is False
            assert view.induced_slot('name', c).range == 'string'
            self.assertEqual(view.induced_slot('id', c).owner, c, 'owner does not match')
            self.assertEqual(view.induced_slot('name', c).owner, c, 'owner does not match')
        for c in ['Event', 'EmploymentEvent', 'MedicalEvent']:
            s = view.induced_slot('started at time', c)
            logging.debug(f's={s.range} // c = {c}')
            assert s.range == 'date'
            assert s.slot_uri == 'prov:startedAtTime'
            self.assertEqual(s.owner, c, 'owner does not match')
            c_induced = view.induced_class(c)
            # an induced class should have no slots
            assert c_induced.slots == []
            assert c_induced.attributes != []
            s2 = c_induced.attributes['started at time']
            assert s2.range == 'date'
            assert s2.slot_uri == 'prov:startedAtTime'
        # test slot_usage
        assert view.induced_slot('age in years', 'Person').minimum_value == 0
        assert view.induced_slot('age in years', 'Adult').minimum_value == 16
        assert view.induced_slot('name', 'Person').pattern is not None
        assert view.induced_slot('type', 'FamilialRelationship').range == 'FamilialRelationshipType'
        assert view.induced_slot('related to', 'FamilialRelationship').range == 'Person'
        assert view.get_slot('related to').range == 'Thing'
        assert view.induced_slot('related to', 'Relationship').range == 'Thing'

        a = view.get_class('activity')
        self.assertCountEqual(a.exact_mappings, ['prov:Activity'])
        logging.debug(view.get_mappings('activity', expand=True))
        self.assertCountEqual(view.get_mappings('activity')['exact'], ['prov:Activity'])
        self.assertCountEqual(view.get_mappings('activity', expand=True)['exact'], ['http://www.w3.org/ns/prov#Activity'])

        u = view.usage_index()
        for k, v in u.items():
            #print(f' {k} = {v}')
            logging.debug(f' {k} = {v}')
        assert SchemaUsage(used_by='FamilialRelationship', slot='related to',
                           metaslot='range', used='Person', inferred=False) in u['Person']

        # test methods also work for attributes
        leaves = view.class_leaves()
        logging.debug(f'LEAVES={leaves}')
        assert 'MedicalEvent' in leaves
        roots = view.class_roots()
        logging.debug(f'ROOTS={roots}')
        assert 'Dataset' in roots
        ds_slots = view.class_slots('Dataset')
        logging.debug(ds_slots)
        assert len(ds_slots) == 3
        self.assertCountEqual(['persons', 'companies', 'activities'], ds_slots)
        for sn in ds_slots:
            s = view.induced_slot(sn, 'Dataset')
            logging.debug(s)

    def test_rollup_rolldown(self):
        # no import schema
        view = SchemaView(SCHEMA_NO_IMPORTS)
        element_name = 'Event'
        roll_up(view, element_name)
        for slot in view.class_induced_slots(element_name):
            logging.debug(slot)
        induced_slot_names = [s.name for s in view.class_induced_slots(element_name)]
        logging.debug(induced_slot_names)
        self.assertCountEqual(['started at time', 'ended at time', 'is current', 'in location', 'employed at', 'married to'],
                              induced_slot_names)
        # check to make sure rolled-up classes are deleted
        assert view.class_descendants(element_name, reflexive=False) == []
        roll_down(view, view.class_leaves())

        for element_name in view.all_classes():
            c = view.get_class(element_name)
            logging.debug(f'{element_name}')
            logging.debug(f'  {element_name} SLOTS(i) = {view.class_slots(element_name)}')
            logging.debug(f'  {element_name} SLOTS(d) = {view.class_slots(element_name, direct=True)}')
            self.assertCountEqual(view.class_slots(element_name), view.class_slots(element_name, direct=True))
        assert 'Thing' not in view.all_classes()
        assert 'Person' not in view.all_classes()
        assert 'Adult' in view.all_classes()
        
    def test_caching(self):
        """
        Determine if cache is reset after modifications made to schema
        """
        schema = SchemaDefinition(id='test', name='test')
        view = SchemaView(schema)
        self.assertCountEqual([], view.all_classes())
        view.add_class(ClassDefinition('X'))
        self.assertCountEqual(['X'], view.all_classes())
        view.add_class(ClassDefinition('Y'))
        self.assertCountEqual(['X', 'Y'], view.all_classes())
        # bypass view method and add directly to schema;
        # in general this is not recommended as the cache will
        # not be updated
        view.schema.classes['Z'] = ClassDefinition('Z')
        # as expected, the view doesn't know about Z
        self.assertCountEqual(['X', 'Y'], view.all_classes())
        # inform the view modifications have been made
        view.set_modified()
        # should be in sync
        self.assertCountEqual(['X', 'Y', 'Z'], view.all_classes())
        # recommended way to make updates
        view.delete_class('X')
        # cache will be up to date
        self.assertCountEqual(['Y', 'Z'], view.all_classes())
        view.add_class(ClassDefinition('W'))
        self.assertCountEqual(['Y', 'Z', 'W'], view.all_classes())

    def test_imports(self):
        """
        view should by default dynamically include imports chain
        """
        view = SchemaView(SCHEMA_WITH_IMPORTS)
        logging.debug(view.imports_closure())
        self.assertCountEqual(['kitchen_sink', 'core', 'linkml:types'], view.imports_closure())
        for t in view.all_types().keys():
            logging.debug(f'T={t} in={view.in_schema(t)}')
        assert view.in_schema('Person') == 'kitchen_sink'
        assert view.in_schema('id') == 'core'
        assert view.in_schema('name') == 'core'
        assert view.in_schema('activity') == 'core'
        assert view.in_schema('string') == 'types'
        assert 'activity' in view.all_classes()
        assert 'activity' not in view.all_classes(imports=False)

        for c in ['Company', 'Person', 'Organization', 'Thing']:
            assert view.induced_slot('id', c).identifier is True
            assert view.induced_slot('name', c).identifier is not True
            assert view.induced_slot('name', c).required is False
            assert view.induced_slot('name', c).range == 'string'
        for c in ['Event', 'EmploymentEvent', 'MedicalEvent']:
            s = view.induced_slot('started at time', c)
            #print(f's={s.range} // c = {c}')
            assert s.range == 'date'
            assert s.slot_uri == 'prov:startedAtTime'
        assert view.induced_slot('age in years', 'Person').minimum_value == 0
        assert view.induced_slot('age in years', 'Adult').minimum_value == 16

        assert view.get_class('agent').class_uri == 'prov:Agent'
        assert view.get_uri('agent') == 'prov:Agent'
        logging.debug(view.get_class('Company').class_uri)

        assert view.get_uri('Company') == 'ks:Company'
        assert view.get_uri('Company', expand=True) == 'https://w3id.org/linkml/tests/kitchen_sink/Company'
        logging.debug(view.get_uri("TestClass"))
        assert view.get_uri('TestClass') == 'core:TestClass'
        assert view.get_uri('TestClass', expand=True) == 'https://w3id.org/linkml/tests/core/TestClass'

        assert view.get_uri('string') == 'xsd:string'

    def test_merge_imports(self):
        """
        ensure merging and merging imports closure works
        """
        view = SchemaView(SCHEMA_WITH_IMPORTS)
        all_c = copy(view.all_classes())
        all_c_noi = copy(view.all_classes(imports=False))
        assert len(all_c_noi) < len(all_c)
        view.merge_imports()
        all_c2 = copy(view.all_classes())
        self.assertCountEqual(all_c, all_c2)
        all_c2_noi = copy(view.all_classes(imports=False))
        assert len(all_c2_noi) == len(all_c2)

    def test_slot_inheritance(self):
        schema = SchemaDefinition(id='test', name='test')
        view = SchemaView(schema)
        view.add_class(ClassDefinition('C', slots=['s1', 's2']))
        view.add_class(ClassDefinition('D'))
        view.add_class(ClassDefinition('Z'))
        view.add_class(ClassDefinition('W'))
        #view.add_class(ClassDefinition('C2',
        #                               is_a='C')
        #                              # slot_usage=[SlotDefinition(s1, range='C2')])
        view.add_slot(SlotDefinition('s1', multivalued=True, range='D'))
        view.add_slot(SlotDefinition('s2', is_a='s1'))
        view.add_slot(SlotDefinition('s3', is_a='s2', mixins=['m1']))
        view.add_slot(SlotDefinition('s4', is_a='s2', mixins=['m1'], range='W'))
        view.add_slot(SlotDefinition('m1', mixin=True, multivalued=False, range='Z'))
        slot1 = view.induced_slot('s1', 'C')
        assert not slot1.is_a
        self.assertEqual('D', slot1.range)
        assert slot1.multivalued
        slot2 = view.induced_slot('s2', 'C')
        self.assertEqual(slot2.is_a, 's1')
        self.assertEqual('D', slot2.range)
        assert slot2.multivalued
        slot3 = view.induced_slot('s3', 'C')
        assert slot3.multivalued
        self.assertEqual('Z', slot3.range)
        slot4 = view.induced_slot('s4', 'C')
        assert slot4.multivalued
        self.assertEqual('W', slot4.range)
        # test dangling
        view.add_slot(SlotDefinition('s5', is_a='does-not-exist'))
        with self.assertRaises(ValueError):
            view.slot_ancestors('s5')



    def test_metamodel_in_schemaview(self):
        view = package_schemaview('linkml_runtime.linkml_model.meta')
        for cn in ['class_definition', 'type_definition', 'slot_definition']:
            assert cn in view.all_classes()
            assert cn in view.all_classes(imports=False)
            assert view.get_identifier_slot(cn).name == 'name'
        for cn in ['annotation', 'extension']:
            assert cn in view.all_classes()
            assert cn not in view.all_classes(imports=False)
        for sn in ['id', 'name', 'description']:
            assert sn in view.all_slots()
        for tn in ['uriorcurie', 'string', 'float']:
            assert tn in view.all_types()
        for tn in ['uriorcurie', 'string', 'float']:
            assert tn not in view.all_types(imports=False)
        for cn, c in view.all_classes().items():
            uri = view.get_uri(cn, expand=True)
            #print(f'{cn}: {c.class_uri} // {uri}')
            self.assertIsNotNone(uri)
            if cn != 'structured_alias':
                self.assertIn('https://w3id.org/linkml/', uri)
            induced_slots = view.class_induced_slots(cn)
            for s in induced_slots:
                exp_slot_uri = view.get_uri(s, expand=True)
                #print(f'  {cn}: {s.name} {s.alias} {s.slot_uri} // {exp_slot_uri}')
                self.assertIsNotNone(exp_slot_uri)





if __name__ == '__main__':
    unittest.main()
