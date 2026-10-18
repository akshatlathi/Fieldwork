"""Geometry checks shared by record ingestion and evidence consumers."""


def valid_box(box: list[int]) -> bool:
    """A crop must have positive area and stay within normalized frame bounds."""
    return (len(box) == 4 and 0 <= box[0] < box[2] <= 1000
            and 0 <= box[1] < box[3] <= 1000)
