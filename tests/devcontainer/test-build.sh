#/bin/bash
if [ -n "$MSYSTEM" ]; then
    export MSYS2_ARG_CONV_EXCL='*'
    # export MSYS2_ENV_CONV_EXCL='*'
fi
devcontainer up
