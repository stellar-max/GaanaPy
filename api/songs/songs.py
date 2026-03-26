import asyncio
import json


class Songs:
    async def search_songs(self, search_query: str, limit: int) -> list:
        aiohttp = self.aiohttp
        endpoints = self.api_endpoints
        errors = self.errors

        try:
            response = await aiohttp.post(endpoints.search_songs_url + str(search_query).strip())
        except Exception:
            return await errors.no_results()

        try:
            text = await response.text()
        except Exception:
            return await errors.no_results()

        if getattr(response, "status", 200) != 200:
            return await errors.no_results()

        try:
            result = json.loads(text)
        except Exception:
            return await errors.no_results()

        track_ids = []
        try:
            items = result.get("gr", [])[0].get("gd", [])
        except Exception:
            items = []

        try:
            max_limit = int(limit)
        except Exception:
            max_limit = 1

        for item in items[:max_limit]:
            try:
                seo = str(item.get("seo") or "").strip()
                if seo:
                    track_ids.append(seo)
            except Exception:
                continue

        if not track_ids:
            return await errors.no_results()

        track_info = await self.get_track_info(track_ids)
        if not track_info:
            return await errors.no_results()
        return track_info

    async def get_track_info(self, track_id: list) -> list:
        aiohttp = self.aiohttp
        endpoints = self.api_endpoints

        track_info = []

        for i in track_id:
            seokey = str(i or "").strip()
            if not seokey:
                continue

            try:
                response = await aiohttp.post(endpoints.song_details_url + seokey)
            except Exception:
                continue

            try:
                text = await response.text()
            except Exception:
                continue

            if getattr(response, "status", 200) != 200:
                continue

            try:
                result = json.loads(text)
            except Exception:
                continue

            tracks = result.get("tracks") or []
            if not isinstance(tracks, list) or not tracks:
                continue

            formatted = await asyncio.gather(
                *[self.format_json_songs(item) for item in tracks],
                return_exceptions=True,
            )

            for item in formatted:
                if isinstance(item, dict) and item:
                    track_info.append(item)

        return track_info

    async def format_json_songs(self, results: dict) -> dict:
        functions = self.functions
        errors = self.errors

        if not isinstance(results, dict):
            return {}

        data = {}

        try:
            data["seokey"] = results["seokey"]
        except KeyError:
            try:
                return await errors.invalid_seokey()
            except Exception:
                return {}

        data["album_seokey"] = results.get("albumseokey", "")
        data["track_id"] = results.get("track_id", "")
        data["title"] = results.get("track_title", "")

        try:
            data["artists"] = await functions.findArtistNames(results.get("artist", []))
        except Exception:
            data["artists"] = ""

        try:
            data["artist_seokeys"] = await functions.findArtistSeoKeys(results.get("artist", []))
        except Exception:
            data["artist_seokeys"] = []

        try:
            data["artist_ids"] = await functions.findArtistIds(results.get("artist", []))
        except Exception:
            data["artist_ids"] = []

        try:
            artist_detail = results.get("artist_detail") or []
            data["artist_image"] = artist_detail[0].get("atw", "") if artist_detail else ""
        except Exception:
            data["artist_image"] = ""

        data["album"] = results.get("album_title", "")
        data["album_id"] = results.get("album_id", "")
        data["duration"] = results.get("duration", "")
        data["popularity"] = results.get("popularity", "")

        try:
            data["genres"] = await functions.findGenres(results.get("gener", []))
        except Exception:
            data["genres"] = []

        try:
            data["is_explicit"] = await functions.isExplicit(results.get("parental_warning", ""))
        except Exception:
            data["is_explicit"] = False

        data["language"] = results.get("language", "")
        data["label"] = results.get("vendor_name", "")
        data["release_date"] = results.get("release_date", "")
        data["play_count"] = results.get("play_ct", "")
        data["favorite_count"] = results.get("total_favourite_count", "")
        data["song_url"] = f"https://gaana.com/song/{data['seokey']}"
        data["album_url"] = f"https://gaana.com/album/{data['album_seokey']}" if data["album_seokey"] else ""
        data["images"] = {"urls": {}}
        data["images"]["urls"]["large_artwork"] = results.get("artwork_large", "")
        data["images"]["urls"]["medium_artwork"] = results.get("artwork_web", "")
        data["images"]["urls"]["small_artwork"] = results.get("artwork", "")
        data["stream_urls"] = {"urls": {}}

        try:
            encrypted = (((results.get("urls") or {}).get("medium") or {}).get("message") or "")
            if encrypted:
                base_url = await functions.decryptLink(encrypted)
                data["stream_urls"]["urls"]["very_high_quality"] = base_url.replace("64.mp4", "320.mp4")
                data["stream_urls"]["urls"]["high_quality"] = base_url.replace("64.mp4", "128.mp4")
                data["stream_urls"]["urls"]["medium_quality"] = base_url
                data["stream_urls"]["urls"]["low_quality"] = base_url.replace("64.mp4", "16.mp4")
            else:
                data["stream_urls"]["urls"]["very_high_quality"] = ""
                data["stream_urls"]["urls"]["high_quality"] = ""
                data["stream_urls"]["urls"]["medium_quality"] = ""
                data["stream_urls"]["urls"]["low_quality"] = ""
        except Exception:
            data["stream_urls"]["urls"]["very_high_quality"] = ""
            data["stream_urls"]["urls"]["high_quality"] = ""
            data["stream_urls"]["urls"]["medium_quality"] = ""
            data["stream_urls"]["urls"]["low_quality"] = ""

        return data
