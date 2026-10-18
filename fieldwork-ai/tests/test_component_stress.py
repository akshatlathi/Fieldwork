"""Ablation and failure-accounting checks require no model weights or network."""
import cv2
import numpy as np
from fieldwork.unbox import diff
from eval.component_stress import summarise


def test_colour_ablation_does_not_invoke_dino(tmp_path,monkeypatch):
    def unexpected(*args):raise AssertionError("Colour-only must not invoke DINO")
    monkeypatch.setattr(diff,"_dino_map",unexpected)
    image=np.full((140,140,3),180,np.uint8)
    changed=image.copy();changed[40:80,40:80]=(20,60,130)
    reference,target=tmp_path/"ref.png",tmp_path/"new.png"
    cv2.imwrite(str(reference),image);cv2.imwrite(str(target),changed)
    assert diff.change_regions(reference,target,method="colour")


def test_failed_alignment_counts_as_missed_candidate():
    rows=[{"variant":"painted_mark","combined":{"top3_hit":True,"threshold_hit":True}},
          {"variant":"painted_mark","aligned":False}]
    measured=summarise(rows)
    assert measured["combined"]["mark_top3_recall"]["k"]==1
    assert measured["combined"]["mark_top3_recall"]["n"]==2
