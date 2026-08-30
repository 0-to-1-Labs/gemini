import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "generate.py"
SPEC = importlib.util.spec_from_file_location("nanobanana_generate", MODULE_PATH)
generate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate)


class GenerateTests(unittest.TestCase):
    def test_gemini_remains_the_default_provider(self):
        args = generate.parse_args(["a test image"])

        self.assertEqual(args.provider, "gemini")
        self.assertEqual(generate.resolve_options(args), generate.DEFAULT_MODEL)

    def test_atlas_rejects_reference_images(self):
        args = generate.parse_args(
            ["edit this image", "--provider", "atlas", "--image", "input.png"]
        )

        with self.assertRaisesRegex(ValueError, "does not support --image"):
            generate.resolve_options(args)

    @mock.patch.object(generate, "_download_atlas_image", return_value=(b"image", ".jpg"))
    @mock.patch.object(generate.time, "sleep")
    @mock.patch.object(generate, "validate_atlas_model")
    @mock.patch.object(generate, "_atlas_json_request")
    def test_paid_atlas_post_has_no_retry(
        self, json_request, _validate_model, _sleep, _download
    ):
        json_request.side_effect = [
            {"data": {"id": "prediction-1"}},
            {"data": {"status": "completed", "outputs": ["https://example/image"]}},
        ]

        with mock.patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-key"}, clear=True):
            result = generate.generate_atlas_image(
                "a poster", generate.ATLAS_MODEL, resolution="2K"
            )

        self.assertEqual(result, (b"image", ".jpg"))
        post_request = json_request.call_args_list[0].args[0]
        self.assertEqual(post_request.get_method(), "POST")
        self.assertEqual(json.loads(post_request.data)["resolution"], "2k")
        self.assertEqual(json_request.call_args_list[0].kwargs["transient_retries"], 0)
        prediction_request = json_request.call_args_list[1].args[0]
        self.assertEqual(prediction_request.get_method(), "GET")
        self.assertEqual(json_request.call_args_list[1].kwargs["transient_retries"], 2)

    def test_image_suffix_uses_file_signature(self):
        self.assertEqual(generate._image_suffix(b"\xff\xd8\xffsome-jpeg"), ".jpg")
        self.assertEqual(
            generate._image_suffix(b"\x89PNG\r\n\x1a\nrest-of-png"), ".png"
        )


if __name__ == "__main__":
    unittest.main()
