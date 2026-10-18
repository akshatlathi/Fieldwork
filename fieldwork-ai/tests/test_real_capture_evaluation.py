"""Keep incomplete cases and missing temporal coverage visible in evaluations."""
from eval.organized_captures import photo_summary
from eval.temporal_coverage import time_bin_frames
from fieldwork.take.frames import Frame


def test_failed_positive_is_retained_in_detection_denominator():
    rows=[{'track':'photos','owner_reports_defect':True,'status':'failed'},
          {'track':'photos','owner_reports_defect':True,'record':{'capture':{'code_seen':True}},
           'shown_defects':[{'code':'hole'}]}]
    result=photo_summary(rows)
    assert result['photo_api_completed']['k']==1
    assert result['photo_api_completed']['n']==2
    assert result['owner_positive_with_any_shown_defect']['k']==1
    assert result['owner_positive_with_any_shown_defect']['n']==2
    assert result['owner_positive_processing_failures']==1


def test_time_bins_keep_early_view_even_if_late_views_are_sharper():
    frames=[Frame(str(i),None,float(i),1. if i<4 else 100.,120.) for i in range(8)]
    chosen=time_bin_frames(frames,k=2)
    assert len(chosen)==2 and chosen[0].t<4 and chosen[1].t>=4


def test_missing_usable_time_interval_remains_missing():
    frames=[Frame('dark',None,0.,100.,0.),Frame('good',None,7.,10.,120.)]
    assert [f.frame_id for f in time_bin_frames(frames,k=2)]==['good']
