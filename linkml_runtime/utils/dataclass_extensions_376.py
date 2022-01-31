import sys

if sys.version_info < (3, 7, 0):
    raise NotImplementedError("LinkML requires Python 3.7 or later to run")
elif sys.version_info >= (3, 10, 0):
    from dataclasses import MISSING, _HAS_DEFAULT_FACTORY, _POST_INIT_NAME, _FIELD_INITVAR, _init_param, _field_init, \
        _create_fn

    def dataclasses_init_fn_with_kwargs(fields, std_fields, kw_only_fields, frozen, has_post_init,
                 self_name, globals, slots):
        # fields contains both real fields and InitVar pseudo-fields.

        # Make sure we don't have fields without defaults following fields
        # with defaults.  This actually would be caught when exec-ing the
        # function source code, but catching it here gives a better error
        # message, and future-proofs us in case we build up the function
        # using ast.

        seen_default = False
        for f in std_fields:
            # Only consider the non-kw-only fields in the __init__ call.
            if f.init:
                if not (f.default is MISSING and f.default_factory is MISSING):
                    seen_default = True
                elif seen_default:
                    raise TypeError(f'non-default argument {f.name!r} '
                                    'follows default argument')

        locals = {f'_type_{f.name}': f.type for f in fields}
        locals.update({
            'MISSING': MISSING,
            '_HAS_DEFAULT_FACTORY': _HAS_DEFAULT_FACTORY,
        })

        body_lines = []
        for f in fields:
            line = _field_init(f, frozen, locals, self_name, slots)
            # line is None means that this field doesn't require
            # initialization (it's a pseudo-field).  Just skip it.
            if line:
                body_lines.append(line)

        # Does this class have a post-init function?
        if has_post_init:
            params_str = ','.join(f.name for f in fields
                                  if f._field_type is _FIELD_INITVAR)
            body_lines.append(f'{self_name}.{_POST_INIT_NAME}({params_str}{", " if params_str else ""} **kwargs)')

        # If no body lines, use 'pass'.
        if not body_lines:
            body_lines = ['pass']

        _init_params = [_init_param(f) for f in std_fields]
        if kw_only_fields:
            # Add the keyword-only args.  Because the * can only be added if
            # there's at least one keyword-only arg, there needs to be a test here
            # (instead of just concatenting the lists together).
            _init_params += ['*']
            _init_params += [_init_param(f) for f in kw_only_fields]
        return _create_fn('__init__',
                          [self_name] + _init_params + ["**kwargs"],
                          body_lines,
                          locals=locals,
                          globals=globals,
                          return_type=None)
elif sys.version_info >= (3, 9, 0):
    from dataclasses import MISSING, _HAS_DEFAULT_FACTORY, _POST_INIT_NAME, _FIELD_INITVAR, _init_param, _field_init, _create_fn


    def dataclasses_init_fn_with_kwargs(fields, frozen, has_post_init, self_name, globals):
        # fields contains both real fields and InitVar pseudo-fields.

        # Make sure we don't have fields without defaults following fields
        # with defaults.  This actually would be caught when exec-ing the
        # function source code, but catching it here gives a better error
        # message, and future-proofs us in case we build up the function
        # using ast.
        seen_default = False
        for f in fields:
            # Only consider fields in the __init__ call.
            if f.init:
                if not (f.default is MISSING and f.default_factory is MISSING):
                    seen_default = True
                elif seen_default:
                    raise TypeError(f'non-default argument {f.name!r} '
                                    'follows default argument')

        locals = {f'_type_{f.name}': f.type for f in fields}
        locals.update({
            'MISSING': MISSING,
            '_HAS_DEFAULT_FACTORY': _HAS_DEFAULT_FACTORY,
        })

        body_lines = []
        for f in fields:
            line = _field_init(f, frozen, locals, self_name)
            # line is None means that this field doesn't require
            # initialization (it's a pseudo-field).  Just skip it.
            if line:
                body_lines.append(line)

        # Does this class have a post-init function?
        if has_post_init:
            params_str = ','.join(f.name for f in fields
                                  if f._field_type is _FIELD_INITVAR)
            body_lines.append(f'{self_name}.{_POST_INIT_NAME}({params_str}{", " if params_str else ""} **kwargs)')

        # If no body lines, use 'pass'.
        if not body_lines:
            body_lines = ['pass']

        return _create_fn('__init__',
                          [self_name] + [_init_param(f) for f in fields if f.init] + ["**kwargs"],
                          body_lines,
                          locals=locals,
                          globals=globals,
                          return_type=None)
elif sys.version_info >= (3, 8, 1):
    from dataclasses import MISSING, _HAS_DEFAULT_FACTORY, _POST_INIT_NAME, _FIELD_INITVAR, _init_param, _field_init, \
        _create_fn

    def dataclasses_init_fn_with_kwargs(fields, frozen, has_post_init, self_name):
        # fields contains both real fields and InitVar pseudo-fields.

        # Make sure we don't have fields without defaults following fields
        # with defaults.  This actually would be caught when exec-ing the
        # function source code, but catching it here gives a better error
        # message, and future-proofs us in case we build up the function
        # using ast.
        seen_default = False
        for f in fields:
            # Only consider fields in the __init__ call.
            if f.init:
                if not (f.default is MISSING and f.default_factory is MISSING):
                    seen_default = True
                elif seen_default:
                    raise TypeError(f'non-default argument {f.name!r} '
                                    'follows default argument')

        globals = {'MISSING': MISSING,
                   '_HAS_DEFAULT_FACTORY': _HAS_DEFAULT_FACTORY}

        body_lines = []
        for f in fields:
            line = _field_init(f, frozen, globals, self_name)
            # line is None means that this field doesn't require
            # initialization (it's a pseudo-field).  Just skip it.
            if line:
                body_lines.append(line)

        # Does this class have a post-init function?
        if has_post_init:
            params_str = ','.join(f.name for f in fields
                                  if f._field_type is _FIELD_INITVAR)
            body_lines.append(f'{self_name}.{_POST_INIT_NAME}({params_str}{", " if params_str else ""} **kwargs)')

    # If no body lines, use 'pass'.
        if not body_lines:
            body_lines = ['pass']

        locals = {f'_type_{f.name}': f.type for f in fields}
        return _create_fn('__init__',
                          [self_name] + [_init_param(f) for f in fields if f.init] + ["**kwargs"],
                          body_lines,
                          locals=locals,
                          globals=globals,
                          return_type=None)
else:
    from dataclasses import MISSING, _HAS_DEFAULT_FACTORY, _POST_INIT_NAME, _FIELD_INITVAR, _init_param, _field_init, \
        _create_fn

    def dataclasses_init_fn_with_kwargs(fields, frozen, has_post_init, self_name, globals):
        # fields contains both real fields and InitVar pseudo-fields.

        # Make sure we don't have fields without defaults following fields
        # with defaults.  This actually would be caught when exec-ing the
        # function source code, but catching it here gives a better error
        # message, and future-proofs us in case we build up the function
        # using ast.
        seen_default = False
        for f in fields:
            # Only consider fields in the __init__ call.
            if f.init:
                if not (f.default is MISSING and f.default_factory is MISSING):
                    seen_default = True
                elif seen_default:
                    raise TypeError(f'non-default argument {f.name!r} '
                                    'follows default argument')

        locals = {f'_type_{f.name}': f.type for f in fields}
        locals.update({
            'MISSING': MISSING,
            '_HAS_DEFAULT_FACTORY': _HAS_DEFAULT_FACTORY,
        })

        body_lines = []
        for f in fields:
            line = _field_init(f, frozen, globals, self_name)
            # line is None means that this field doesn't require
            # initialization (it's a pseudo-field).  Just skip it.
            if line:
                body_lines.append(line)

        # Does this class have a post-init function?
        if has_post_init:
            params_str = ','.join(f.name for f in fields
                                  if f._field_type is _FIELD_INITVAR)
            body_lines.append(f'{self_name}.{_POST_INIT_NAME}({params_str}{", " if params_str else ""} **kwargs)')

        # If no body lines, use 'pass'.
        if not body_lines:
            body_lines = ['pass']

        return _create_fn('__init__',
                          [self_name] + [_init_param(f) for f in fields if f.init] + ["**kwargs"],
                          body_lines,
                          locals=locals,
                          globals=globals,
                          return_type=None)
