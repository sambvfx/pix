#! /usr/bin/env python
"""
Example script to ingest media provided pix:// links. These urls can be easly
grabbed from the PIX desktop app by right clicking on a file and choosing
"Copy Links".

This example expects you have these python libraries installed:
    - pathlib (https://pypi.org/project/pathlib/)
    - typing (https://pypi.org/project/typing/)

Additionally it requires these external resources:
    - ffmpeg (https://www.ffmpeg.org/)

Examples
--------

Default use:
    python ingest.py "My Project Name" pix://item?50.3527.272761142 pix://item?22.3527.273122402

Specify an output directory:
    python ingest.py -d /path/to/folder "My Project Name" pix://item?50.3527.272761142
"""
from __future__ import print_function

import os
import datetime

import pathlib

import pix

from typing import *


@pix.register('PIXProject')
class MyPIXProject(pix.model.PIXProject):
    """
    Custom base PIXProject base class.
    """
    def get_ingest_dir(self, date=None):
        # type: (Optional[str]) -> pathlib.Path
        """
        Get the note ingestion path.

        Parameters
        ----------
        date : Optional[str]
            e.g. '2018.04.03'

        Returns
        -------
        pathlib.Path
        """
        if date is None:
            date = datetime.datetime.today().strftime('%Y.%m.%d')

        # '~/projects/pix/samples/projects/{PROJECT_NAME}/notes/2018.04.03'
        return pathlib.Path(
            os.path.expandvars(os.path.expanduser(os.path.join(
                '~',
                'projects',
                'pix',
                'samples',
                'projects',
                self.identifier,
                'notes',
                date
            )))
        )

    def _ingest_image(self, directory, item):
        """
        Parameters
        ----------
        directory : pathlib.Path
            Directory where to gather all the images.
        item : PIXImage
            The PIXImage to ingest.

        Returns
        -------
        List[str]
            List of output paths for all markup notes.
        """
        results = []

        for note in item.get_notes():

            with self.session.header({'Accept': 'image/png'}):
                result = self.session.get('/media/{}/composite'.format(
                    note['id']))

            # Make sure we got back a proper response.
            assert result.status_code == 200, result.reason

            # Generate a unique name
            outpath = directory / '{}_{}.png'.format(
                item['fields']['name'], note.identifier)

            with open(str(outpath), 'wb') as f:
                f.write(result.content)

            results.append(outpath)

        return results

    def _ingest_clip(self, directory, item):
        """
        Parameters
        ----------
        directory : pathlib.Path
            Directory where to gather all the images.
        item : PIXClip
            The PIXClip to ingest.

        Returns
        -------
        List[str]
            List of output paths output.
        """
        import shutil
        from collections import defaultdict

        tmpdir = directory / '{}_tmp'.format(item['fields']['name'])
        tmpdir.mkdir()

        markup = defaultdict(list)  # type: DefaultDict[int, List[str]]

        output = directory / '{}_composite.{}'.format(
            *os.path.splitext(item['fields']['name']))

        try:

            with self.session.header({'Accept': 'video/quicktime'}):
                result = self.session.get('/media/{}/original'.format(item['id']))

                # Make sure we got back a proper result.
                assert result.status_code == 200, result.reason

                outpath = tmpdir / 'original.mov'

                # Write the mov file
                with open(str(outpath), 'wb') as f:
                    f.write(result.content)

                base = outpath

            for note in item.get_notes():
                with self.session.header({'Accept': 'image/png'}):
                    result = self.session.get('/media/{}/markup.png'.format(
                        note['id']))

                # Make sure we got back a proper response.
                assert result.status_code == 200, result.reason

                # Get the output path.
                frame = note['fields']['start_frame']
                outpath = tmpdir / '{}_markup.{}.png'.format(
                    item['fields']['name'], frame)

                with open(str(outpath), 'wb') as f:
                    f.write(result.content)

                markup[frame].append(str(outpath))

            if not markup:
                base.rename(output)
            else:
                output = stitch(str(base), markup, str(output))

        finally:
            shutil.rmtree(str(tmpdir))

        return output

    def ingest_from_app_urls(self, urls, directory=None):
        """
        Saves all marked down image notes.

        Parameters
        ----------
        urls : List[str]
            Links to specific notes to get. 
            Formatted like pix://item?22.3546.269939680
        directory : Optional[Union[str, pathlib.Path]]
            Directory where to gather all the images.

        Returns
        -------
        List[str]
            List of all files created.
        """
        results = []

        if directory is not None and not isinstance(directory, pathlib.Path):
            directory = pathlib.Path(directory)
        else:
            directory = self.get_ingest_dir()
        if not directory.exists():
            directory.mkdir(parents=True)

        for url in urls:
            itemid = url.rsplit('.', 1)[-1]
            item = self.load_item(itemid)
            if not item:
                print('\nNo item found for {!r}'.format(url))
                continue
            print('\nIngesting {!r}'.format(item))
            if item['class'] == 'PIXClip':
                results.append(self._ingest_clip(directory, item))
            elif item['class'] == 'PIXImage':
                results.extend(self._ingest_image(directory, item))

        return results


def stitch(base, markup, output):
    """
    Overlay a clip with per-frame markup images.

    Parameters
    ----------
    base : str
    markup : Dict[int, List[str]]
    output : str

    Returns
    -------
    str
    """
    import subprocess

    assert os.path.exists(str(base))

    cmd = [
        'ffmpeg',
        '-y',
    ]

    cmd.extend(['-i', '"{}"'.format(str(base))])
    for lm in markup.values():
        for m in lm:
            assert os.path.exists(str(m))
            cmd.extend(['-i', '"{}"'.format(str(m))])

    last = '[0]'
    fltrs = []
    for i, (frame, lm) in enumerate(markup.items()):
        for _ in lm:
            name = '[v{}]'.format(i + 1)
            fltrs.append(
                "{last}[{i}]overlay=enable='eq(n,{frame})'{name}".format(
                    last=last, i=i + 1, frame=frame, name=name))
            last = name

    cmd.extend([
        '-filter_complex', '"{}"'.format('; '.join(fltrs))
    ])

    cmd.extend([
        '-map', '{!r}'.format(last),
        '-map', '0:a'
    ])

    cmd.append('"{}"'.format(output))

    print(' '.join(cmd))
    proc = subprocess.Popen(' '.join(cmd), shell=True)
    proc.wait()

    assert os.path.exists(str(output))
    return str(output)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Ingest media from pix app urls.',
        epilog=__doc__
    )

    parser.add_argument('project', type=str)
    parser.add_argument('urls', type=str, nargs='*')
    parser.add_argument('-d', '--directory', type=str)

    args = parser.parse_args()
    with pix.Session() as session:
        project = session.load_project(args.project)  # type: MyPIXProject
        project.ingest_from_app_urls(args.urls, directory=args.directory or None)
