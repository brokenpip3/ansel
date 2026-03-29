# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/brokenpip3/ansel/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                         |    Stmts |     Miss |   Cover |   Missing |
|----------------------------- | -------: | -------: | ------: | --------: |
| ansel/\_\_main\_\_.py        |        3 |        0 |    100% |           |
| ansel/browser.py             |       24 |        0 |    100% |           |
| ansel/cli.py                 |      328 |       53 |     84% |55-58, 93-94, 156-158, 262-264, 359, 367-369, 388, 406-412, 435-437, 464, 480-492, 512, 525-526, 528-529, 532-535, 540-542, 554-565, 587-588, 620 |
| ansel/config.py              |      266 |       27 |     90% |22, 24, 46-47, 68, 108, 111, 114, 139, 144, 160, 177, 197-198, 221, 235, 271, 301, 311, 337, 346-348, 354-355, 370-372 |
| ansel/diff.py                |       28 |        0 |    100% |           |
| ansel/exceptions.py          |       13 |        1 |     92% |        14 |
| ansel/github.py              |       45 |        1 |     98% |        63 |
| ansel/hooks/\_\_init\_\_.py  |        3 |        0 |    100% |           |
| ansel/hooks/builtin.py       |       40 |        0 |    100% |           |
| ansel/hooks/manager.py       |       75 |        8 |     89% |72-73, 126-128, 131-132, 144 |
| ansel/patch/engines/base.py  |       10 |        1 |     90% |        17 |
| ansel/patch/engines/regex.py |       18 |        0 |    100% |           |
| ansel/patch/engines/toml.py  |      115 |       31 |     73% |55-60, 62-67, 103-104, 124-125, 128-133, 140-149 |
| ansel/patch/engines/yaml.py  |      166 |       15 |     91% |63-64, 67-70, 101-102, 176-177, 222-230 |
| ansel/patch/manager.py       |       35 |        1 |     97% |        38 |
| ansel/repo.py                |       63 |       11 |     83% |38-39, 45-49, 66-67, 77-78 |
| ansel/template.py            |      132 |       20 |     85% |79-80, 105-116, 140-141, 153-154, 175-185 |
| ansel/ui.py                  |       84 |        7 |     92% |24, 26, 32, 119-123, 129 |
| **TOTAL**                    | **1448** |  **176** | **88%** |           |

3 empty files skipped.


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/brokenpip3/ansel/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/brokenpip3/ansel/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/brokenpip3/ansel/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/brokenpip3/ansel/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fbrokenpip3%2Fansel%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/brokenpip3/ansel/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.