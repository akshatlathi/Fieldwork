from eval.defect_sequence import ContextResponse, Judgment, agreement_policy, proposals, reconcile


def test_union_keeps_baseline_only_and_regional_uncertainty():
    row = {'baseline': {'findings': [{'code': 'hole', 'evidence': [{'frame_id': 'p1', 'box_2d': [100, 100, 200, 200]}]}]}}
    photo = {'photo': 'p1', 'candidate': {'findings': [{'code': 'stain', 'source_box_2d': [300, 300, 400, 400], 'status': 'uncertain'}]}}
    items, invalid = proposals(row, photo)
    assert not invalid and [p['code'] for p in items] == ['hole', 'stain']
    assert items[1]['origins'][0]['initial_status'] == 'uncertain'


def test_overlap_dedup_retains_both_origins():
    row = {'baseline': {'findings': [{'code': 'hole', 'evidence': [{'frame_id': 'p1', 'box_2d': [100, 100, 200, 200]}]}]}}
    photo = {'photo': 'p1', 'candidate': {'findings': [{'code': 'hole', 'source_box_2d': [100, 100, 200, 200], 'status': 'visible_defect'}]}}
    items, _ = proposals(row, photo)
    assert len(items) == 1 and len(items[0]['origins']) == 2


def test_missing_duplicate_and_invented_ids_cannot_create_support():
    items = [{'id': 'c0', 'code': 'hole'}, {'id': 'c1', 'code': 'stain'}]
    response = ContextResponse(judgments=[Judgment(candidate_id=id, status='supported', reason='test') for id in ['c0', 'c0', 'invented']])
    output, unknown = reconcile(items, response)
    assert all(p['context']['status'] == 'uncertain' for p in output)
    assert len(unknown) == 1


def test_invalid_geometry_excluded_and_rejection_never_upgraded():
    photo = {'photo': 'p1', 'candidate': {'findings': [{'code': 'hole', 'source_box_2d': [200, 100, 100, 200], 'status': 'visible_defect'}]}}
    items, invalid = proposals({}, photo)
    assert not items and len(invalid) == 1
    output, _ = reconcile([{'id': 'c0', 'code': 'hole'}], ContextResponse(judgments=[Judgment(candidate_id='c0', status='not_supported', reason='print')]))
    assert output[0]['context']['status'] == 'not_supported'


def test_agreement_policy_does_not_promote_detector_uncertainty():
    p = {'origins': [{'initial_status': 'uncertain'}], 'context': {'status': 'supported'}}
    assert agreement_policy(p) == 'uncertain'
    p['origins'].append({'initial_status': 'visible_defect'})
    assert agreement_policy(p) == 'supported'
    p['context']['status'] = 'uncertain'
    assert agreement_policy(p) == 'uncertain'
    p['context']['status'] = 'not_supported'
    assert agreement_policy(p) == 'not_supported'
