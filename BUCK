# Copyright 2024. WebPros International GmbH. All rights reserved.
# vim:ft=python:

include_defs('//product.defs.py')


python_binary(
    name = 'ubuntu20to22.pex',
    platform = 'py3',
    # libgcc_s.so.1 is preloaded to workaround crash due to "libgcc_s.so.1 must
    # be installed for pthread_cancel to work" instead of clean exit after
    # dist-upgrade, see https://bugs.python.org/issue44434
    build_args = ['--python-shebang', '/usr/bin/env -S LD_PRELOAD=libgcc_s.so.1 python3'],
    main_module = 'ubuntu20to22.main',
    deps = [
        'dist-upgrader//pleskdistup:lib',
        '//ubuntu20to22:lib',
    ],
)

genrule(
    name = 'ubuntu20to22',
    srcs = [':ubuntu20to22.pex'],
    out = 'ubuntu20to22',
    cmd = 'cp $(location :ubuntu20to22.pex) $OUT && chmod +x $OUT',
)
