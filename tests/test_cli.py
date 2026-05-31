"""CLI tests: backward-compat single mode + new `recipe` subcommand."""

from pantrypath.cli import main


def test_single_mode_backward_compatible(capsys):
    rc = main(["--need", "buttermilk", "--have", "milk,white_vinegar"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "buttermilk" in out and "0.15" in out


def test_recipe_subcommand_text(capsys):
    rc = main([
        "recipe",
        "--have", "all_purpose_flour,milk,white_vinegar,sugar",
        "--recipe-text", "2 cups all-purpose flour\n1 cup buttermilk\n1 tsp vanilla extract",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "菜谱解析结果" in out
    assert "buttermilk" in out          # missing -> solved
    assert "vanilla" in out             # unmatched -> reported
    assert "all_purpose_flour" in out   # already have


def test_recipe_file(tmp_path, capsys):
    f = tmp_path / "recipe.txt"
    f.write_text("1 cup buttermilk\n2 cups cake flour\n", encoding="utf-8")
    rc = main([
        "recipe",
        "--have", "powdered_milk,water,white_vinegar,all_purpose_flour,cornstarch",
        "--recipe-file", str(f),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "buttermilk" in out and "cake_flour" in out


def test_recipe_empty_input_returns_2(capsys):
    rc = main(["recipe", "--have", "milk", "--recipe-text", "   "])
    assert rc == 2


def test_top_k_flag_shows_alternatives(capsys):
    rc = main(["--need", "buttermilk",
               "--have", "milk,white_vinegar,lemon_juice,plain_yogurt,water",
               "--top-k", "3"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "备选方案" in out and "最省" in out and "备选2" in out
