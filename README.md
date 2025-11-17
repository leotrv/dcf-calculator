
dcf-calculator
==============

Quickstart
----------

1. Clone the repository:

```bash
git clone https://github.com/leotrv/dcf-calculator.git
cd dcf-calculator
```

2. Development run (recommended `uv` flow):

If you use `uv` in your environment, the simplest flow is:

```bash
uv sync
```

`uv sync` will synchronize the project environment and run the repository's defined tasks — in typical setups this prepares dependencies and starts the development server. If you don't use `uv`, you can run the `poe` task directly:

```bash
# start development server via poe
poe dev
```

API conventions and units
-------------------------

- Cash amounts: `starting_fcf`, `net_debt`, and `terminal_value` are expressed in billions. Example: `72.764` means 72.764 billion.
- Rates: `fcf_growth_rate`, `discount_rate`, and `terminal_growth_rate` are expressed in percent. Example: `8.0` means 8%.
- `starting_fcf` semantics: represents the last historical year's free cash flow. The first forecast year (FCF1) is computed as `starting_fcf * (1 + fcf_growth_rate)`.
- `net_debt`: positive means net debt (company owes more than cash); negative means net cash (company holds more cash than it owes).

Example request payload (JSON):

```json
{
	"starting_fcf": 72.764,
	"fcf_growth_rate": 8.0,
	"years": 10,
	"discount_rate": 8.0,
	"terminal_growth_rate": 3.0,
	"net_debt": -54.3
}
```

What the API returns
-------------------

- `discounted_fcfs`: present-value of each forecasted FCF (discounted by the discount rate). Note this is not the raw forecasted series — if growth rate equals discount rate the PVs may equal the same number as shown by the math.
- `discounted_terminal_value`: present-value of the terminal value (if any).
- `enterprise_value` / `equity_value`: sums derived from the PVs and net debt.

Running tests
-------------

Run unit tests with:

```bash
PYTHONPATH=. pytest -q
```
