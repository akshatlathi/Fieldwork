"""Evidence geometry must survive EXIF orientation, tile mapping and bad outputs."""
from PIL import Image
import pytest

from eval.regional_defects import Finding, Inspection, map_findings, prepare_views, source_box


def test_exif_upright_tile_coordinates(tmp_path):
    src = tmp_path/'phone.jpg'
    image = Image.new('RGB', (100, 200))
    exif = Image.Exif(); exif[274] = 6
    image.save(src, exif=exif)
    views = prepare_views(src, tmp_path/'views')
    assert views[0]['source_size_wh'] == [200, 100]
    assert Image.open(views[0]['path']).size == (200, 100)
    assert source_box([0, 0, 1000, 1000], views[4]) == [400, 400, 1000, 1000]
    assert source_box([250, 250, 750, 750], views[4]) == [550, 550, 850, 850]


@pytest.mark.parametrize('box', [[900, 0, 100, 1000], [0, -1, 100, 100], [0, 0, 0, 100], [0, 0, 1001, 100]])
def test_invalid_boxes_rejected(box):
    with pytest.raises(ValueError):
        source_box(box, {'pixel_box_xyxy': [0, 0, 100, 100], 'source_size_wh': [100, 100]})


def test_unknown_views_and_reversed_boxes_cannot_become_evidence():
    base = dict(code='hole', region='front', status='visible_defect', severity='minor', note='candidate')
    result = Inspection(findings=[Finding(view_id='invented', box_2d=[0, 0, 100, 100], **base),
                                  Finding(view_id='overview', box_2d=[100, 0, 0, 100], **base)])
    mapped = map_findings(result, [{'id': 'overview', 'pixel_box_xyxy': [0, 0, 100, 100], 'source_size_wh': [100, 100]}])
    assert not mapped['findings'] and len(mapped['rejected']) == 2


def test_overlap_dedup_keeps_uncertain_separate():
    base = dict(code='hole', region='front', severity='minor', note='candidate')
    result = Inspection(findings=[Finding(view_id='overview', box_2d=[100, 100, 200, 200], status=status, **base)
                                  for status in ['visible_defect', 'visible_defect', 'uncertain']])
    mapped = map_findings(result, [{'id': 'overview', 'pixel_box_xyxy': [0, 0, 100, 100], 'source_size_wh': [100, 100]}])
    assert len(mapped['findings']) == 2 and len(mapped['duplicates']) == 1
