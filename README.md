# Project 3

### Setup

Start with installing uv, uv is a modern python package manager.

- [UV Install instructions](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)

Using brew:
```bash
brew install uv
```

### Running the simulator

```bash
uv run main.py <CLI_ARGS>
```

---

### CLI Arguments

The simulation can be configured using a variety of command-line arguments. If no arguments are provided, the simulation will run with a default set of parameters.

#### General Options

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--gui` | `False` | Launches the graphical user interface to visualize the simulation. If omitted, the simulation runs in the command line and outputs a JSON blob. |
| `--turns` | `100` | Sets the total number of days the garden gets to cultivate. |
| `--count` | `20` | Sets the number of plants (only works with the --random flag). |
| `--json_path` | `No default` | Specify the seed and plant variations of a simulation. |
| `--seed` | `No default` | Provides a seed for the random number generator to ensure reproducible simulations. |

#### Gardener Configuration

The `--gardener` argument allows you to specify the gardener which will cultivate the garden

- **Format:** `--gardener <TYPE>`
- **`<TYPE>`:** A short code representing the player type.

##### Available Gardener Types

| Code | Gardener Type |
| :--- | :--- |
| `gr` | RandomGardener |
| `g1`-`g10` | Player0 through Player11 |

---

### Code Quality and Formatting

The repository uses Ruff for both formatting and linting, if your PR does not pass the CI checks it won't be merged.

VSCode has a Ruff extension that can run on save. [Editor Setup](https://docs.astral.sh/ruff/editors/setup/).

To run formatting check:

```bash
uv run ruff format --check
```

To run formatting:

```bash
uv run ruff format
```

To run linting:

```bash
uv run ruff check
```

To run linting with auto-fix:

```bash
uv run ruff check --fix
```

---

### Usage Examples

Here are some common examples of how to run the simulation with different configurations.

##### Example 1: Run with the GUI

To run the simulation and see the visualizer, use the `--gui` flag. This example also increases the number of turns using the RandomGardener.

```bash
uv run python main.py --random --gui --turns 200 --gardener gr
```

##### Example 2: Run a Simulation with JSON file

To create a simulation using the JSON file, and increase the number of turns in the simulation. No GUI.

```bash
uv run python main.py --json_path /path/to/my.json --turns 200 --gardener gr
```
