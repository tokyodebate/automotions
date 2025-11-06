# Automated Motion Query
This program allows the scraping of motions and the statistics from Tabbycat.

## Functionalities
- Fetches rounds, motions, and statistics from Tabbycat
- Copies the data into clipboard
- Copies table format data into clipboard
- Write data into cloned/forked version of [tokodebate/motions](https://github.com/tokyodebate/motions)

## Usage
This program uses [uv](https://docs.astral.sh/uv/) as its manager.
1. Clone this repository and change directory to the cloned repository
    ```sh
    $ git clone https://github.com/tokyodebate/automotions
    $ cd automotions
    ```

2. Run `uv sync` to load libraries
    ```sh
    uv sync
    ```

3. Additionally, to enable direct modification of [tokyodebate/motions](https://github.com/tokyodebate/motions), clone the repository somewhere
    ```sh
    cd ~
    git clone https://github.com/tokyodebate/motions
    ```

4. Run `main.py`
    ```sh
    uv run main.py
    ```

5. Follow the instructions.
    1. Enter the URL of the tab to fetch data from
    2. Select tournament if necessary
    3. Select tournament type. Usually, **automatic** should detect the type
    4. Select the output format
        - **Copy text data to clipboard** will copy the data, in the desired `.txt` format, to the clipboard
        - **Copy table data to clipboard** will copy the data, in table/csv format, to the clipboard.
        - **Save to tokyodebate/motions repository** will save the data to a locally cloned tokyodebate/motions repository.
    5. (For saving to tokyodebate/motions repository) Enter the path to tokyodebate/motions repository, relative to the current path (which this repository is in)
    6. Select the tournament group. If this is a new tournament, type "New"
    7. Enter information
    8. When finished, make sure to stage, commit, and push all changes in the motions repository.
        ```sh
        cd PATH_TO_MOTIONS_REPOSITORY
        git add .
        git commit -m "SOME_MESSAGE"
        git push
        ```

6. You can exit the code with `Ctrl+C`