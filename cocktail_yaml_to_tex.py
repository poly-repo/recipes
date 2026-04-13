"""Backward-compatible wrapper for recipe_yaml_to_tex.

Usage:
    bazel run //people/mav/recipes:cocktail_yaml_to_tex -- path/to/file.yaml
"""

from recipe_yaml_to_tex import main


if __name__ == "__main__":
    main()
