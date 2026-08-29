import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from prepare_sample import response_schema,build_prompt,validate_no_leakage,QUESTION_TEXT
from run_openrouter import deterministic_mock,validate_payload,validate_request_rows
class PipelineTests(unittest.TestCase):
    def test_schema_keys(self):
        s=response_schema();self.assertEqual(set(s["required"]),set(QUESTION_TEXT));self.assertFalse(s["additionalProperties"])
    def test_prompt_has_all_questions(self):
        p=build_prompt("You are a 30-year-old woman living in rural Bihar, India.")
        for q in QUESTION_TEXT.values():self.assertIn(q,p)
    def test_leakage_guard(self):
        validate_no_leakage("You are a 30-year-old woman living in rural Bihar, India.")
        with self.assertRaises(AssertionError):validate_no_leakage("You use the internet every day.")
    def test_mock_payload_validates(self):
        r={"anon_id":"CAMS-00001","condition":"rich","persona":"x","prompt":"x"};validate_payload(deterministic_mock(r))
    def test_duplicate_guard(self):
        r={"anon_id":"CAMS-00001","condition":"rich","persona":"x","prompt":"x"}
        with self.assertRaises(AssertionError):validate_request_rows([r,r])
if __name__=="__main__":unittest.main()
