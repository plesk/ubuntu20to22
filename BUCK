# Copyright 1999-2026. Plesk International GmbH. All rights reserved.
# vim:ft=python:

include_defs('//product.defs.py')


python_binary(
    name = 'ubuntu22to24.pex',
    platform = 'py3',
    # libgcc_s.so.1 is preloaded to workaround crash due to "libgcc_s.so.1 must
    # be installed for pthread_cancel to work" instead of clean exit after
    # dist-upgrade, see https://bugs.python.org/issue44434
    build_args = ['--python-shebang', '/usr/bin/env -S LD_PRELOAD=libgcc_s.so.1 python3'],
    main_module = 'ubuntu22to24.main',
    deps = [
        'dist-upgrader//pleskdistup:lib',
        '//ubuntu22to24:lib',
    ],
)

genrule(
    name = 'ubuntu22to24',
    srcs = [':ubuntu22to24.pex'],
    out = 'ubuntu22to24',
    cmd = 'cp $(location :ubuntu22to24.pex) $OUT && chmod +x $OUT',
)
