import unittest

from greeter import MAX_NAME_LENGTH, greet


class GreetTests(unittest.TestCase):
    def test_greets_name(self):
        self.assertEqual(greet("Tom"), "Hello, Tom!")

    def test_strips_whitespace(self):
        self.assertEqual(greet("  Tom \n"), "Hello, Tom!")

    def test_keeps_non_ascii_names(self):
        self.assertEqual(greet("Ærlige Åse"), "Hello, Ærlige Åse!")

    def test_accepts_name_at_max_length(self):
        name = "a" * MAX_NAME_LENGTH
        self.assertEqual(greet(name), f"Hello, {name}!")

    def test_rejects_empty_name(self):
        for name in ("", "   ", "\t\n"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                greet(name)

    def test_rejects_too_long_name(self):
        with self.assertRaises(ValueError):
            greet("a" * (MAX_NAME_LENGTH + 1))

    def test_rejects_non_string(self):
        for name in (None, 42, ["Tom"]):
            with self.subTest(name=name), self.assertRaises(TypeError):
                greet(name)


if __name__ == "__main__":
    unittest.main()
