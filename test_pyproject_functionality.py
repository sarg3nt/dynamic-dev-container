#!/usr/bin/env python3
"""Simple test to verify pyproject field updating functionality."""


def test_package_name_conversion():
    """Test package name conversion logic."""

    def convert_package_name(package_name: str) -> tuple[str, str]:
        """Convert package name to valid formats."""
        if package_name and package_name.strip():
            package_name_clean = package_name.lower().replace("-", "_").replace(" ", "_")
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
        else:
            # Use defaults for empty package name
            package_name_clean = "my_awesome_project"
            package_name_url = "my-awesome-project"
        return package_name_clean, package_name_url

    # Test various package names
    test_cases = [
        ("my-awesome-project", "my_awesome_project", "my-awesome-project"),
        ("My Cool Package", "my_cool_package", "my-cool-package"),
        ("simple", "simple", "simple"),
        ("test_package", "test_package", "test-package"),
        ("", "my_awesome_project", "my-awesome-project"),
    ]

    print("Testing package name conversion:")
    for input_name, expected_clean, expected_url in test_cases:
        clean, url = convert_package_name(input_name)
        print(
            f"Input: '{input_name}' -> Clean: '{clean}' (expected: '{expected_clean}'), URL: '{url}' (expected: '{expected_url}')"
        )
        assert clean == expected_clean, f"Clean conversion failed for '{input_name}'"
        assert url == expected_url, f"URL conversion failed for '{input_name}'"

    print("✅ Package name conversion tests passed!")


def test_url_generation():
    """Test URL generation logic."""

    def generate_urls(package_name_url: str) -> dict[str, str]:
        """Generate URLs based on package name."""
        return {
            "homepage": f"https://github.com/yourusername/{package_name_url}",
            "source": f"https://github.com/yourusername/{package_name_url}",
            "documentation": f"https://github.com/yourusername/{package_name_url}/README.md",
            "package_path": f"src/{package_name_url.replace('-', '_')}",
        }

    # Test URL generation
    test_package = "my-cool-project"
    urls = generate_urls(test_package)

    print("\nTesting URL generation:")
    print(f"Package: {test_package}")
    for url_type, url in urls.items():
        print(f"  {url_type}: {url}")

    expected_urls = {
        "homepage": "https://github.com/yourusername/my-cool-project",
        "source": "https://github.com/yourusername/my-cool-project",
        "documentation": "https://github.com/yourusername/my-cool-project/README.md",
        "package_path": "src/my_cool_project",
    }

    for url_type, expected in expected_urls.items():
        assert urls[url_type] == expected, f"URL generation failed for {url_type}"

    print("✅ URL generation tests passed!")


def test_should_update_logic():
    """Test the should_update logic for field replacement."""

    def should_update_field(current_value: str, field_type: str) -> bool:
        """Test logic for whether a field should be updated."""
        if field_type == "homepage":
            return (
                not current_value
                or current_value == "https://github.com/yourusername/my-awesome-project"
                or "my-awesome-project" in current_value
                or "yourusername" in current_value
                or current_value.startswith("https://github.com/yourusername/")
            )
        if field_type == "package_path":
            return (
                not current_value
                or current_value == "src/my_awesome_project"
                or "my_awesome_project" in current_value
                or current_value.startswith("src/")
            )
        return False

    print("\nTesting should_update logic:")

    # Test cases: (current_value, field_type, should_update)
    test_cases = [
        ("", "homepage", True),
        ("https://github.com/yourusername/my-awesome-project", "homepage", True),
        ("https://github.com/yourusername/some-old-project", "homepage", True),
        ("https://github.com/realuser/my-awesome-project", "homepage", True),
        ("https://github.com/realuser/custom-project", "homepage", False),
        ("src/my_awesome_project", "package_path", True),
        ("src/some_other_project", "package_path", True),
        ("custom/path", "package_path", False),
    ]

    for current_value, field_type, expected in test_cases:
        result = should_update_field(current_value, field_type)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{current_value}' ({field_type}) -> {result} (expected: {expected})")
        if result != expected:
            print(f"      FAILED: Expected {expected}, got {result}")

    print("✅ Should_update logic tests completed!")


if __name__ == "__main__":
    test_package_name_conversion()
    test_url_generation()
    test_should_update_logic()
    print("\n🎉 All tests completed!")
