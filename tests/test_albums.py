from __future__ import annotations

from soundseek_core.albums import build_album_sections, build_metadata_albums
from tests.conftest import make_track
from web_app.album_presenters import (
    build_albums_view,
    cover_data_uri,
    format_album_detail,
)


def test_type_albums_include_all_content_types_and_tracks() -> None:
    tracks = [
        make_track("music-1", "Song", content_type="music"),
        make_track("music-2", "Another song", content_type="music"),
        make_track("speech-1", "Talk", content_type="speech"),
        make_track("nature-1", "Rain", content_type="nature"),
    ]

    type_albums, _ = build_album_sections(tracks)

    assert [album.content_type for album in type_albums] == [
        "music",
        "speech",
        "nature",
    ]
    assert [album.track_count for album in type_albums] == [2, 1, 1]


def test_metadata_albums_need_at_least_two_tracks() -> None:
    tracks = [
        make_track(
            "a",
            "First",
            "Artist",
            album="Same Album",
            album_artist="Artist",
            track_number=2,
        ),
        make_track(
            "b",
            "Second",
            "Artist",
            album="Same Album",
            album_artist="Artist",
            track_number=1,
        ),
        make_track(
            "c",
            "Single",
            "Artist",
            album="Only One",
            album_artist="Artist",
        ),
    ]

    albums = build_metadata_albums(tracks)

    assert len(albums) == 1
    assert albums[0].title == "Same Album"
    assert albums[0].track_count == 2
    assert [track.id for track in albums[0].tracks] == ["b", "a"]


def test_same_album_name_with_different_album_artists_is_not_merged() -> None:
    tracks = [
        make_track("a", "A", "Artist A", album="Live", album_artist="Artist A"),
        make_track("b", "B", "Artist B", album="Live", album_artist="Artist B"),
    ]

    assert build_metadata_albums(tracks) == []


def test_album_view_separates_type_and_metadata_sections() -> None:
    tracks = [
        make_track("a", "A", "Artist", album="Record", album_artist="Artist"),
        make_track("b", "B", "Artist", album="Record", album_artist="Artist"),
        make_track("c", "C", "Artist", content_type="speech"),
    ]
    type_albums, metadata_albums = build_album_sections(tracks)

    html = build_albums_view(type_albums, metadata_albums)
    detail = format_album_detail(metadata_albums[0])

    assert "По типам контента" in html
    assert "Альбомы из метаданных" in html
    assert 'data-album-key="type:music"' in html
    assert "Музыка" in html
    assert "Record" in html
    assert "soundseek-album-tracklist" in detail
    assert 'data-track-play="a"' in detail
    assert 'data-track-play="b"' in detail
    assert "A" in detail and "B" in detail


def test_cover_data_uri_is_embedded_for_album_card(tmp_path) -> None:
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"fake-jpeg")
    tracks = [
        make_track(
            "a",
            "A",
            "Artist",
            album="Record",
            album_artist="Artist",
            cover_path=str(cover),
        ),
        make_track(
            "b",
            "B",
            "Artist",
            album="Record",
            album_artist="Artist",
        ),
    ]
    _, metadata_albums = build_album_sections(tracks)

    html = build_albums_view([], metadata_albums)

    assert cover_data_uri(str(cover)).startswith("data:image/jpeg;base64,")
    assert "data:image/jpeg;base64," in html
