# Allen Institute Software License - This software license is the 2-clause BSD
# license plus a third clause that prohibits redistribution for commercial
# purposes without further permission.
#
# Copyright 2016-2017. Allen Institute. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Redistributions for commercial purposes are not permitted without the
# Allen Institute's written permission.
# For purposes of this license, commercial purposes is the incorporation of the
# Allen Institute's software into anything for which you will charge fees or
# other compensation. Contact terms@alleninstitute.org for commercial licensing
# opportunities.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
import pytest
from mock import MagicMock, patch, mock_open
from allensdk.api.cache import Cache, cacheable
from allensdk.api.queries.rma_api import RmaApi
import allensdk.core.json_utilities as ju
import pandas as pd
import pandas.io.json as pj
from six.moves import builtins
from allensdk.config.manifest import Manifest

try:
    import StringIO
except:
    import io as StringIO
import os


_msg = [{'whatever': True}]
_pd_msg = pd.DataFrame(_msg)
_csv_msg = pd.DataFrame.from_csv(StringIO.StringIO(""",whatever
0,True
"""))


@pytest.fixture
def mock_read_json():
    pj.read_json = \
        MagicMock(name='read_json',
                  return_value=_pd_msg)

    return pj.read_json


@pytest.fixture
def mock_dataframe():
    pd.DataFrame.to_csv = \
        MagicMock(name='to_csv')

    pd.DataFrame.from_csv = \
        MagicMock(name='from_csv',
                  return_value=_csv_msg)

    return pd.DataFrame


@pytest.fixture
def mock_json_utilities():
    ju.read_url_get = \
        MagicMock(name='read_url_get',
                  return_value={'msg': _msg})
    ju.write = \
        MagicMock(name='write')

    ju.read = \
        MagicMock(name='read',
                  return_value=_msg)

    return ju


@patch('csv.DictWriter')
@patch.object(pd.DataFrame, 'from_csv')
def test_cacheable_csv_dataframe(from_csv,
                                 dictwriter,
                                 mock_json_utilities,
                                 mock_dataframe):
    @cacheable()
    def get_hemispheres():
        return RmaApi().model_query(model='Hemisphere')

    with patch('allensdk.config.manifest.Manifest.safe_mkdir') as mkdir:
        with patch(builtins.__name__ + '.open',
                   mock_open(),
                   create=True) as open_mock:
            open_mock.return_value.write = MagicMock()
            df = get_hemispheres(path='/xyz/abc/example.txt',
                                 strategy='create',
                                 **Cache.cache_csv_dataframe())

    assert df.loc[:, 'whatever'][0]

    mock_json_utilities.read_url_get.assert_called_once_with(
        'http://api.brain-map.org/api/v2/data/query.json?q=model::Hemisphere')
    mock_dataframe.from_csv.assert_called_once_with('/xyz/abc/example.txt')
    assert not mock_json_utilities.write.called, 'write should not have been called'
    assert not mock_json_utilities.read.called, 'read should not have been called'
    mkdir.assert_called_once_with('/xyz/abc')
    open_mock.assert_called_once_with('/xyz/abc/example.txt', 'w')


@patch.object(pd.DataFrame, 'from_csv')
@patch.object(Manifest, 'safe_mkdir')
def test_cacheable_json(from_csv, mkdir,
                        mock_json_utilities,
                        mock_dataframe):
    @cacheable()
    def get_hemispheres():
        return RmaApi().model_query(model='Hemisphere')

    df = get_hemispheres(path='/xyz/abc/example.json',
                         strategy='create',
                         **Cache.cache_json())

    assert 'whatever' in df[0]

    mock_json_utilities.read_url_get.assert_called_once_with(
        'http://api.brain-map.org/api/v2/data/query.json?q=model::Hemisphere')
    assert not mock_dataframe.from_csv.called, 'from_csv should not have been called'
    mock_json_utilities.write.assert_called_once_with('/xyz/abc/example.json',
                                                      _msg)
    mock_json_utilities.read.assert_called_once_with('/xyz/abc/example.json')


@patch.object(Manifest, 'safe_mkdir')
def test_excpt(mkdir,
               mock_json_utilities,
               mock_dataframe):
    @cacheable()
    def get_hemispheres_excpt():
        return RmaApi().model_query(model='Hemisphere',
                                    excpt=['symbol'])

    df = get_hemispheres_excpt(path='/xyz/abc/example.json',
                         strategy='create',
                         **Cache.cache_json())

    assert 'whatever' in df[0]

    mock_json_utilities.read_url_get.assert_called_once_with(
        'http://api.brain-map.org/api/v2/data/query.json?q=model::Hemisphere,rma::options%5Bexcept$eqsymbol%5D')
    mock_json_utilities.write.assert_called_once_with('/xyz/abc/example.json',
                                                      _msg)
    mock_json_utilities.read.assert_called_once_with('/xyz/abc/example.json')
    mkdir.assert_called_once_with('/xyz/abc')


def test_cacheable_no_cache_csv(mock_json_utilities,
                                mock_dataframe):
    @cacheable()
    def get_hemispheres():
        return RmaApi().model_query(model='Hemisphere')

    df = get_hemispheres(path='/xyz/abc/example.csv',
                         strategy='file',
                         **Cache.cache_csv())

    assert df.loc[:, 'whatever'][0]

    assert not mock_json_utilities.read_url_get.called
    mock_dataframe.from_csv.assert_called_once_with('/xyz/abc/example.csv')
    assert not mock_json_utilities.write.called, 'json write should not have been called'
    assert not mock_json_utilities.read.called, 'json read should not have been called'


@patch.object(Manifest, 'safe_mkdir')
def test_cacheable_json_dataframe(mkdir,
                                  mock_json_utilities,
                                  mock_dataframe,
                                  mock_read_json):
    @cacheable()
    def get_hemispheres():
        return RmaApi().model_query(model='Hemisphere')

    df = get_hemispheres(path='/xyz/abc/example.json',
                         strategy='create',
                         **Cache.cache_json_dataframe())

    assert df.loc[:, 'whatever'][0]

    mock_json_utilities.read_url_get.assert_called_once_with(
        'http://api.brain-map.org/api/v2/data/query.json?q=model::Hemisphere')
    assert not mock_dataframe.from_csv.called, 'from_csv should not have been called'
    mock_read_json.assert_called_once_with('/xyz/abc/example.json',
                                      orient='records')
    mock_json_utilities.write.assert_called_once_with('/xyz/abc/example.json', _msg)
    assert not mock_json_utilities.read.called, 'json read should not have been called'
    mkdir.assert_called_once_with('/xyz/abc')

@patch('csv.DictWriter')
@patch.object(Manifest, 'safe_mkdir')
def test_cacheable_csv_json(mkdir, dictwriter,
                            mock_json_utilities,
                            mock_dataframe,
                            mock_read_json):
    @cacheable()
    def get_hemispheres():
        return RmaApi().model_query(model='Hemisphere')

    with patch(builtins.__name__ + '.open',
               mock_open(),
               create=True) as open_mock:
        open_mock.return_value.write = MagicMock()
        df = get_hemispheres(path='/xyz/example.csv',
                             strategy='create',
                             **Cache.cache_csv_json())

    assert 'whatever' in df[0]

    mock_json_utilities.read_url_get.assert_called_once_with(
        'http://api.brain-map.org/api/v2/data/query.json?q=model::Hemisphere')
    mock_dataframe.from_csv.assert_called_once_with('/xyz/example.csv')
    dictwriter.return_value.writerow.assert_called()
    assert not mock_read_json.called, 'pj.read_json should not have been called'
    assert not mock_json_utilities.write.called, 'ju.write should not have been called'
    assert not mock_json_utilities.read.called, 'json read should not have been called'
    mkdir.assert_called_once_with('/xyz')
    open_mock.assert_called_once_with('/xyz/example.csv', 'w')


def test_cacheable_no_save(mock_json_utilities,
                           mock_dataframe):
    @cacheable()
    def get_hemispheres():
        return RmaApi().model_query(model='Hemisphere')

    data = get_hemispheres()

    assert 'whatever' in data[0]

    mock_json_utilities.read_url_get.assert_called_once_with(
        'http://api.brain-map.org/api/v2/data/query.json?q=model::Hemisphere')
    assert not mock_dataframe.to_csv.called, 'to_csv should not have been called'
    assert not mock_dataframe.from_csv.called, 'from_csv should not have been called'
    assert not mock_json_utilities.write.called, 'json write should not have been called'
    assert not mock_json_utilities.read.called, 'json read should not have been called'


def test_cacheable_no_save_dataframe(mock_json_utilities,
                                     mock_dataframe):
    @cacheable()
    def get_hemispheres():
        return RmaApi().model_query(model='Hemisphere')

    df = get_hemispheres(**Cache.nocache_dataframe())

    assert df.loc[:, 'whatever'][0]

    mock_json_utilities.read_url_get.assert_called_once_with(
        'http://api.brain-map.org/api/v2/data/query.json?q=model::Hemisphere')
    assert not mock_dataframe.to_csv.called, 'to_csv should not have been called'
    assert not mock_dataframe.from_csv.called, 'from_csv should not have been called'
    assert not mock_json_utilities.write.called, 'json write should not have been called'
    assert not mock_json_utilities.read.called, 'json read should not have been called'


@patch('csv.DictWriter')
@patch.object(Manifest, 'safe_mkdir')
def test_cacheable_lazy_csv_no_file(mkdir, dictwriter,
                                    mock_json_utilities,
                                    mock_dataframe):
    @cacheable()
    def get_hemispheres():
        return RmaApi().model_query(model='Hemisphere')

    with patch('os.path.exists', MagicMock(return_value=False)) as ope:
        with patch(builtins.__name__ + '.open',
                   mock_open(),
                   create=True) as open_mock:
            open_mock.return_value.write = MagicMock()
            df = get_hemispheres(path='/xyz/abc/example.csv',
                                 strategy='lazy',
                                 **Cache.cache_csv())

    assert df.loc[:, 'whatever'][0]

    mock_json_utilities.read_url_get.assert_called_once_with(
        'http://api.brain-map.org/api/v2/data/query.json?q=model::Hemisphere')
    open_mock.assert_called_once_with('/xyz/abc/example.csv', 'w')
    dictwriter.return_value.writerow.assert_called()
    mock_dataframe.from_csv.assert_called_once_with('/xyz/abc/example.csv')
    assert not mock_json_utilities.write.called, 'json write should not have been called'
    assert not mock_json_utilities.read.called, 'json read should not have been called'


def test_cacheable_lazy_csv_file_exists(mock_json_utilities,
                                        mock_dataframe):
    @cacheable()
    def get_hemispheres():
        return RmaApi().model_query(model='Hemisphere')

    with patch('os.path.exists', MagicMock(return_value=True)) as ope:
        df = get_hemispheres(path='/xyz/abc/example.csv',
                             strategy='lazy',
                             **Cache.cache_csv())

    assert df.loc[:, 'whatever'][0]

    assert not mock_json_utilities.read_url_get.called
    mock_dataframe.from_csv.assert_called_once_with('/xyz/abc/example.csv')
    assert not mock_json_utilities.write.called, 'json write should not have been called'
    assert not mock_json_utilities.read.called, 'json read should not have been called'