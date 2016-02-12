# The MIT License (MIT)
#
# Copyright (c) 2016 WUSTL ZPLAB
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors: Erik Hvatum <ice.rikh@gmail.com>

import argparse
import enum
from pathlib import Path

SOURCE_5X_DPATH = Path('/mnt/scopearray/Sinha_Drew/20160209_N2Acquisition_1_5x/')

class ZStackAction(enum.Enum):
    CopyZStacks = 0
    MoveZStacks = 1
    IgnoreZStacks = 2

def pull_files(zstack_action, include_newest_zstacks, copy_metadata, copy_calibrations, copy_other_data):
    pass

if __name__ == '__main__':
    import sys
    parser = argparse.ArgumentParser(
        description='Move z stack images and/or copy other image files and metadata from 20160209_N2Acquisition experiment '
                    'directories to our reorganized local directory structure.')
    parser.add_argument('--include-newest-zstacks', action='store_true')
    parser.add_argument('--copy-zstacks', action='store_true')
    parser.add_argument('--move-zstacks', action='store_true')
    parser.add_argument('--copy-metadata', action='store_true')
    parser.add_argument('--copy-calibrations', action='store_true')
    parser.add_argument('--copy-other-data', action='store_true')
    args = parser.parse_args()
    if args.copy_zstacks and args.move_zstacks:
        print('The --copy-zstacks and --move-zstacks switches are mutually exclusive.\n', file=sys.stderr)
        parser.print_usage(file=sys.stderr)
        sys.exit(-1)
    if not any((args.copy_zstacks, args.move_zstacks, args.copy_metadata, args.copy_calibrations, args.copy_other_data)):
        print('At least one of --copy-zstacks, --move-zstacks, --copy-metadata, --copy-calibrations, and/or '
              '--copy-other-data must be specified.\n', file=sys.stderr)
        parser.print_usage(file=sys.stderr)
        sys.exit(-1)
    if args.copy_zstacks:
        zstack_action = ZStackAction.CopyZStacks
    elif args.move_zstacks:
        zstack_action = ZStackAction.MoveZStacks
    else:
        zstack_action = ZStackAction.IgnoreZStacks
    pull_files(zstack_action, args.include_newest_zstacks, args.copy_metadata, args.copy_calibrations, args.copy_other_data)