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
from datetime import datetime
import enum
import json
from pathlib import Path
import re
import shutil
import time

SOURCE_5X_DPATH = Path('/mnt/scopearray/Sinha_Drew/20160209_N2Acquisition_1_5x')
SOURCE_10X_DPATH = Path('/mnt/scopearray/Sinha_Drew/20160209_N2Acquisition_1_10x')
DESTINATION_DPATH = Path(__file__).parent
JSON_METADATA_LOADING_RETRY_COUNT = 3

class ZStackAction(enum.Enum):
    CopyZStacks = 0
    MoveZStacks = 1
    IgnoreZStacks = 2

JSON_METADATA_LOADING_RETRY_COUNT = 3

def _td_format(td_object):
    """From http://stackoverflow.com/a/538687"""
    seconds = int(td_object.total_seconds())
    periods = [
        ('year',   60*60*24*365),
        ('month',  60*60*24*30),
        ('day',    60*60*24),
        ('hour',   60*60),
        ('minute', 60),
        ('second', 1)]
    strings=[]
    for period_name,period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds,period_seconds)
            if period_value == 1:
                strings.append("%s %s" % (period_value, period_name))
            else:
                strings.append("%s %ss" % (period_value, period_name))
    return ", ".join(strings)

def _load_json_metadata(fpath):
    # Retry if parsing fails in case json file was truncated or absent due to being in the process of being rewritten
    i = 0
    while True:
        try:
            with fpath.open('r') as f:
                json_str = f.read()
                return json_str, json.loads(json_str)
        except FileNotFoundError:
            if i < JSON_METADATA_LOADING_RETRY_COUNT:
                print('Failed to open "{}".  Retrying in 1 second.'.format(fpath), file=sys.stderr)
                time.sleep(1)
            else:
                raise
        except json.JSONDecodeError as e:
            if i < JSON_METADATA_LOADING_RETRY_COUNT:
                print('Failed to parse "{}".  Retrying in 1 second.'.format(fpath), file=sys.stderr)
                time.sleep(1)
            else:
                raise
        i += 1

def _mkdir_for_fpath(fpath, dry_run):
    dpath = fpath.parent
    if not dpath.exists():
        print('mkdir', str(dpath))
        if not dry_run:
            dpath.mkdir(parents=True)

def _should_skip(src_fpath, dst_fpath):
        skip = False
        if not src_fpath.exists():
            skip = True
        elif dst_fpath.exists():
            src_stat = src_fpath.stat()
            dst_stat = dst_fpath.stat()
            skip = (
                src_stat.st_size == dst_stat.st_size and
                src_stat.st_mtime == dst_stat.st_mtime and
                src_stat.st_ctime == dst_stat.st_ctime)
        return skip

def pull_files(zstack_action, copy_metadata, copy_calibrations, copy_other_data, skip_latest_timepoint, dry_run):
    processed_bytecount = 0
    total_bytecount = 0

    def metadata_op(dst_fpath, metadata_str):
        nonlocal processed_bytecount
        _mkdir_for_fpath(dst_fpath, dry_run)
        print('=> "{}"'.format(dst_fpath))
        if not dry_run:
            if dst_fpath.exists():
                dst_fpath.unlink()
            with dst_fpath.open('w') as f:
                print(metadata_str, end='', file=f)
        processed_bytecount += len(metadata_str)
        print('{:.3%}'.format(processed_bytecount / total_bytecount))

    def file_op(src_fpath, dst_fpath, mv_else_cp):
        nonlocal processed_bytecount
        _mkdir_for_fpath(dst_fpath, dry_run)
        bytecount = src_fpath.stat().st_size
        print('{} "{}" -> "{}"... '.format('mv' if mv_else_cp else 'cp', src_fpath, dst_fpath), end='', flush=True)
        if not dry_run:
            if dst_fpath.exists():
                dst_fpath.unlink()
            (shutil.move if mv_else_cp else shutil.copy2)(str(src_fpath), str(dst_fpath))
        t1 = datetime.now()
        processed_bytecount += bytecount
        processed_frac = processed_bytecount / total_bytecount
        unprocessed_frac = 1.0 - processed_frac
        print('{:.3%}, {} remaining'.format(processed_frac, _td_format((t1-t0)*(unprocessed_frac/processed_frac))))

    mv_fpaths = []
    cp_fpaths = []
    metadatas = []

    print('Scanning...')
    for src_exp_dpath, dst_exp_dpath in ((SOURCE_5X_DPATH, DESTINATION_DPATH / '5x'), (SOURCE_10X_DPATH, DESTINATION_DPATH / '10x')):
        metadata_str, metadata = _load_json_metadata(src_exp_dpath / 'experiment_metadata.json')
        timepoints = metadata['timepoints']
        if skip_latest_timepoint and timepoints:
            timepoints.pop()
        position_idxs = sorted(int(k) for k in metadata['positions'].keys())
        print('', str(src_exp_dpath))
        if copy_metadata:
            metadatas.append((dst_exp_dpath / 'experiment_metadata.json', metadata_str))
            src_fpath = src_exp_dpath / 'acquisitions.log'
            dst_fpath = dst_exp_dpath / 'acquisitions.log'
            if not _should_skip(src_fpath, dst_fpath):
                cp_fpaths.append((src_fpath, dst_fpath))
            src_fpath = src_exp_dpath / 'acquire_youngworms-zp3.py'
            dst_fpath = dst_exp_dpath / 'acquire_youngworms-zp3.py'
            if not _should_skip(src_fpath, dst_fpath):
                cp_fpaths.append((src_fpath, dst_fpath))
        for timepoint_idx, timepoint in enumerate(timepoints):
            # if timepoint_idx > 10:
            #     break
            print(' ', timepoint)
            if copy_calibrations:
                def do_calibration_fname(fname):
                    src_fpath = src_exp_dpath / '{} {}'.format(timepoint, fname)
                    dst_fpath = dst_exp_dpath / '{} {}'.format(timepoint, fname)
                    if not _should_skip(src_fpath, dst_fpath):
                        cp_fpaths.append((src_fpath, dst_fpath))
                do_calibration_fname('bf_flatfield.tiff')
                do_calibration_fname('vignette_mask.png')
            for position_idx in position_idxs:
                print('  ', position_idx)
                src_pos_dpath = src_exp_dpath / '{:02}'.format(position_idx)
                dst_pos_dpath = dst_exp_dpath / '{:02}'.format(position_idx)
                if zstack_action != ZStackAction.IgnoreZStacks:
                    stack_dname = '{} focus'.format(timepoint)
                    src_stack_dpath = src_pos_dpath / stack_dname
                    if src_stack_dpath.exists():
                        print('    focus')
                        dst_stack_dpath = dst_pos_dpath / stack_dname
                        xx_fpaths = mv_fpaths if zstack_action is ZStackAction.MoveZStacks else cp_fpaths
                        for src_fpath in sorted(src_stack_dpath.glob('*')):
                            if re.match(r'fine_focus-\d{2}\.tiff', src_fpath.name):
                                dst_fpath = dst_stack_dpath / src_fpath.name
                                if not _should_skip(src_fpath, dst_fpath):
                                    xx_fpaths.append((src_fpath, dst_fpath))
                if copy_metadata and timepoint_idx == 0:
                    pos_metadata_str, pos_metadata = _load_json_metadata(src_pos_dpath / 'position_metadata.json')
                    metadatas.append((dst_pos_dpath / 'position_metadata.json', pos_metadata_str))
                if copy_other_data:
                    src_fpath = src_pos_dpath / '{} bf.tiff'.format(timepoint)
                    dst_fpath = dst_pos_dpath / '{} bf.tiff'.format(timepoint)
                    if not _should_skip(src_fpath, dst_fpath):
                        cp_fpaths.append((src_fpath, dst_fpath))

    total_bytecount = sum(len(metadata_str) for metadata_fpath, metadata_str in metadatas)
    total_bytecount+= sum(fpath[0].stat().st_size for fpaths in (mv_fpaths, cp_fpaths) for fpath in fpaths)
    t0 = datetime.now()

    for dst_fpath, metadata_str in metadatas:
        metadata_op(dst_fpath, metadata_str)
    for src_fpath, dst_fpath in mv_fpaths:
        file_op(src_fpath, dst_fpath, True)
    for src_fpath, dst_fpath in cp_fpaths:
        file_op(src_fpath, dst_fpath, False)

if __name__ == '__main__':
    import sys
    parser = argparse.ArgumentParser(
        description='Move z stack images and/or copy other image files and metadata from 20160209_N2Acquisition experiment '
                    'directories to our reorganized local directory structure.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-latest-timepoint', action='store_true')
    parser.add_argument('--copy-zstacks', action='store_true')
    parser.add_argument('--move-zstacks', action='store_true')
    parser.add_argument('--copy-metadata', action='store_true')
    parser.add_argument('--copy-calibrations', action='store_true')
    parser.add_argument('--copy-other-data', action='store_true')
    args = parser.parse_args()
    if args.copy_zstacks and args.move_zstacks:
        print('--copy-zstacks and --move-zstacks are mutually exclusive.\n', file=sys.stderr)
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
    pull_files(zstack_action, args.copy_metadata, args.copy_calibrations, args.copy_other_data, args.skip_latest_timepoint, args.dry_run)