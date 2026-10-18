"""Phone EXIF orientation must agree across Gemini, embeddings and OpenCV crops."""
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageDraw
import pytest

from fieldwork import gemini
from fieldwork.take import grade


@pytest.mark.parametrize("orientation", [2, 3, 4, 5, 6, 7, 8])
def test_gemini_pixels_follow_same_orientation_as_opencv(tmp_path, orientation):
    image=Image.new('RGB',(100,60),'red')
    ImageDraw.Draw(image).rectangle((50,0,99,59),fill='blue')
    exif=Image.Exif();exif[274]=orientation
    path=tmp_path/'phone.jpg';image.save(path,exif=exif,quality=95)
    original=path.read_bytes()
    part=gemini.image_part(path)
    with Image.open(BytesIO(part.inline_data.data)) as sent:
        pixels=np.array(sent.convert('RGB'))
        assert sent.getexif().get(274,1)==1
    expected=cv2.cvtColor(cv2.imread(str(path)),cv2.COLOR_BGR2RGB)
    assert pixels.shape==expected.shape
    assert np.abs(pixels.astype(float)-expected).mean()<3
    assert path.read_bytes()==original


def test_upright_frame_is_sent_without_reencoding(tmp_path):
    path=tmp_path/'frame.jpg';Image.new('RGB',(80,100),'green').save(path)
    assert gemini.image_part(path).inline_data.data==path.read_bytes()


def test_embeddings_receive_upright_pixels(tmp_path,monkeypatch):
    import torch
    image=Image.new('RGB',(100,60),'red');exif=Image.Exif();exif[274]=6
    path=tmp_path/'phone.jpg';image.save(path,exif=exif)
    seen=[]
    class Processor:
        def __call__(self,images,**kwargs):
            seen.extend(im.size for im in images)
            return {}
    class Model:
        def get_image_features(self,**kwargs):return torch.tensor([[1.,2.]])
    monkeypatch.setattr(grade,'_backbone',lambda:(Processor(),Model()))
    features=grade.embed([path])
    assert seen==[(60,100)]
    assert np.isfinite(features).all()
