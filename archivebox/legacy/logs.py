import os
import sys

from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List

from .schema import Link, ArchiveResult
from .config import ANSI, OUTPUT_DIR, IS_TTY


@dataclass
class RuntimeStats:
    """mutable stats counter for logging archiving timing info to CLI output"""

    skipped: int = 0
    succeeded: int = 0
    failed: int = 0

    parse_start_ts: Optional[datetime] = None
    parse_end_ts: Optional[datetime] = None

    index_start_ts: Optional[datetime] = None
    index_end_ts: Optional[datetime] = None

    archiving_start_ts: Optional[datetime] = None
    archiving_end_ts: Optional[datetime] = None

# globals are bad, mmkay
_LAST_RUN_STATS = RuntimeStats()


def pretty_path(path: str) -> str:
    """convert paths like .../ArchiveBox/archivebox/../output/abc into output/abc"""
    pwd = os.path.abspath('.')
    # parent = os.path.abspath(os.path.join(pwd, os.path.pardir))
    return path.replace(pwd + '/', './')


### Parsing Stage

def log_parsing_started(source_file: str):
    start_ts = datetime.now()
    _LAST_RUN_STATS.parse_start_ts = start_ts
    print('\n{green}[*] [{}] Parsing new links from output/sources/{}...{reset}'.format(
        start_ts.strftime('%Y-%m-%d %H:%M:%S'),
        source_file.rsplit('/', 1)[-1],
        **ANSI,
    ))

def log_parsing_finished(num_parsed: int, num_new_links: int, parser_name: str):
    end_ts = datetime.now()
    _LAST_RUN_STATS.parse_end_ts = end_ts
    print('    > Parsed {} links as {} ({} new links added)'.format(num_parsed, parser_name, num_new_links))


### Indexing Stage

def log_indexing_process_started(num_links: int):
    start_ts = datetime.now()
    _LAST_RUN_STATS.index_start_ts = start_ts
    print()
    print('{green}[*] [{}] Updating {} links in main index...{reset}'.format(
        start_ts.strftime('%Y-%m-%d %H:%M:%S'),
        num_links,
        **ANSI,
    ))

def log_indexing_process_finished():
    end_ts = datetime.now()
    _LAST_RUN_STATS.index_end_ts = end_ts

def log_indexing_started(out_path: str):
    if IS_TTY:
        sys.stdout.write(f'    > {out_path}')

def log_indexing_finished(out_path: str):
    print(f'\r    √ {out_path}')


### Archiving Stage

def log_archiving_started(num_links: int, resume: Optional[float]):
    start_ts = datetime.now()
    _LAST_RUN_STATS.archiving_start_ts = start_ts
    print()
    if resume:
        print('{green}[▶] [{}] Resuming archive updating for {} pages starting from {}...{reset}'.format(
             start_ts.strftime('%Y-%m-%d %H:%M:%S'),
             num_links,
             resume,
             **ANSI,
        ))
    else:
        print('{green}[▶] [{}] Updating content for {} pages in archive...{reset}'.format(
             start_ts.strftime('%Y-%m-%d %H:%M:%S'),
             num_links,
             **ANSI,
        ))

def log_archiving_paused(num_links: int, idx: int, timestamp: str):
    end_ts = datetime.now()
    _LAST_RUN_STATS.archiving_end_ts = end_ts
    print()
    print('\n{lightyellow}[X] [{now}] Downloading paused on link {timestamp} ({idx}/{total}){reset}'.format(
        **ANSI,
        now=end_ts.strftime('%Y-%m-%d %H:%M:%S'),
        idx=idx+1,
        timestamp=timestamp,
        total=num_links,
    ))
    print('    To view your archive, open:')
    print('        {}/index.html'.format(OUTPUT_DIR))
    print('    Continue archiving where you left off by running:')
    print('        archivebox update --resume={}'.format(timestamp))

def log_archiving_finished(num_links: int):
    end_ts = datetime.now()
    _LAST_RUN_STATS.archiving_end_ts = end_ts
    assert _LAST_RUN_STATS.archiving_start_ts is not None
    seconds = end_ts.timestamp() - _LAST_RUN_STATS.archiving_start_ts.timestamp()
    if seconds > 60:
        duration = '{0:.2f} min'.format(seconds / 60, 2)
    else:
        duration = '{0:.2f} sec'.format(seconds, 2)

    print()
    print('{}[√] [{}] Update of {} pages complete ({}){}'.format(
        ANSI['green'],
        end_ts.strftime('%Y-%m-%d %H:%M:%S'),
        num_links,
        duration,
        ANSI['reset'],
    ))
    print('    - {} links skipped'.format(_LAST_RUN_STATS.skipped))
    print('    - {} links updated'.format(_LAST_RUN_STATS.succeeded))
    print('    - {} links had errors'.format(_LAST_RUN_STATS.failed))
    print('    To view your archive, open:')
    print('        {}/index.html'.format(OUTPUT_DIR))


def log_link_archiving_started(link: Link, link_dir: str, is_new: bool):
    # [*] [2019-03-22 13:46:45] "Log Structured Merge Trees - ben stopford"
    #     http://www.benstopford.com/2015/02/14/log-structured-merge-trees/
    #     > output/archive/1478739709

    print('\n[{symbol_color}{symbol}{reset}] [{symbol_color}{now}{reset}] "{title}"'.format(
        symbol_color=ANSI['green' if is_new else 'black'],
        symbol='+' if is_new else '√',
        now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        title=link.title or link.base_url,
        **ANSI,
    ))
    print('    {blue}{url}{reset}'.format(url=link.url, **ANSI))
    print('    {} {}'.format(
        '>' if is_new else '√',
        pretty_path(link_dir),
    ))

def log_link_archiving_finished(link: Link, link_dir: str, is_new: bool, stats: dict):
    total = sum(stats.values())

    if stats['failed'] > 0 :
        _LAST_RUN_STATS.failed += 1
    elif stats['skipped'] == total:
        _LAST_RUN_STATS.skipped += 1
    else:
        _LAST_RUN_STATS.succeeded += 1


def log_archive_method_started(method: str):
    print('      > {}'.format(method))


def log_archive_method_finished(result: ArchiveResult):
    """quote the argument with whitespace in a command so the user can 
       copy-paste the outputted string directly to run the cmd
    """
    # Prettify CMD string and make it safe to copy-paste by quoting arguments
    quoted_cmd = ' '.join(
        '"{}"'.format(arg) if ' ' in arg else arg
        for arg in result.cmd
    )

    if result.status == 'failed':
        # Prettify error output hints string and limit to five lines
        hints = getattr(result.output, 'hints', None) or ()
        if hints:
            hints = hints if isinstance(hints, (list, tuple)) else hints.split('\n')
            hints = (
                '    {}{}{}'.format(ANSI['lightyellow'], line.strip(), ANSI['reset'])
                for line in hints[:5] if line.strip()
            )

        # Collect and prefix output lines with indentation
        output_lines = [
            '{lightred}Failed:{reset}'.format(**ANSI),
            '    {reset}{} {red}{}{reset}'.format(
                result.output.__class__.__name__.replace('ArchiveError', ''),
                result.output, 
                **ANSI,
            ),
            *hints,
            '{}Run to see full output:{}'.format(ANSI['lightred'], ANSI['reset']),
            *(['    cd {};'.format(result.pwd)] if result.pwd else []),
            '    {}'.format(quoted_cmd),
        ]
        print('\n'.join(
            '        {}'.format(line)
            for line in output_lines
            if line
        ))
        print()


def log_list_started(filter_patterns: List[str], filter_type: str):
    print('{green}[*] Finding links in the archive index matching these {} patterns:{reset}'.format(
        filter_type,
        **ANSI,
    ))
    print('    {}'.format(' '.join(filter_patterns)))

def log_list_finished(links):
    from .util import to_csv
    print()
    print('---------------------------------------------------------------------------------------------------')
    print(to_csv(links, csv_cols=['timestamp', 'is_archived', 'num_outputs', 'url'], header=True, ljust=16, separator=' | '))
    print('---------------------------------------------------------------------------------------------------')
    print()


def log_removal_started(links: List[Link], yes: bool, delete: bool):
    print('{lightyellow}[i] Found {} matching URLs to remove.{reset}'.format(len(links), **ANSI))
    if delete:
        file_counts = [link.num_outputs for link in links if os.path.exists(link.link_dir)]
        print(
            f'    {len(links)} Links will be de-listed from the main index, and their archived content folders will be deleted from disk.\n'
            f'    ({len(file_counts)} data folders with {sum(file_counts)} archived files will be deleted!)'
        )
    else:
        print(
            f'    Matching links will be de-listed from the main index, but their archived content folders will remain in place on disk.\n'
            f'    (Pass --delete if you also want to permanently delete the data folders)'
        )

    if not yes:
        print()
        print('{lightyellow}[?] Do you want to proceed with removing these {} links?{reset}'.format(len(links), **ANSI))
        try:
            assert input('    y/[n]: ').lower() == 'y'
        except (KeyboardInterrupt, EOFError, AssertionError):
            raise SystemExit(0)

def log_removal_finished(all_links: int, to_keep: int):
    if all_links == 0:
        print()
        print('{red}[X] No matching links found.{reset}'.format(**ANSI))
    else:
        num_removed = all_links - to_keep
        print()
        print('{red}[√] Removed {} out of {} links from the archive index.{reset}'.format(
            num_removed,
            all_links,
            **ANSI,
        ))
        print('    Index now contains {} links.'.format(to_keep))
