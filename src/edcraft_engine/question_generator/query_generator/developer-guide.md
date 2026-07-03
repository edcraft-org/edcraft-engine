# Query Generator Guide

This document explains the code in greater detail.


## Main Steps

### `generate_query`

This is the method used by users of `QueryGenerator`. It is an orchestration method. It takes in a list of `TargetElement`s and an `output_type` to create a `Query`.

An example input is:

```python
target = [
    TargetElement(
        type="loop",
        id=[0],
        name=None,
        line_number=5,
        modifier="loop_iterations"
    ),
    TargetElement(
        type="function",
        id=[3],
        name: "visited.add",
        line_number: 9,
        modifier: "arguments",
    )
]

output_type = "first"  # list / count / first / last
```

The method applies the following steps:

0. Reset internal state and create a base query. This ensures that previous query generations do not affect the next one.

1. Processes each target in order. 

    In the above example, to handle the first `TargetElement`, all the loop iterations fulfilling the given conditions are found. Then, to handle the second `TargetElement`, within each of the loop iteration, the function calls `visited.add` are found. This is handled by the `_get_target` method.

    The first target is the starting filter, and later targets are joined in relation to earlier ones.

2. Apply the output type using `_apply_output_type` to turn the query into a `count`, `list`, `first` or `last` result.

3. Apply the last target's modifier uisng `_apply_modifier`. 

    This step is required as some modifiers are only applicable for the last target. These are the `arguments` and `return_value` modifiers. These modifiers selects a field from the records, but they do not change which record is selected.

    On the other hand, `_get_target` handles modifiers which affect which records match. These are the `branch_true`, `branch_false` and `loop_iterations` modifiers.

    The `arugments` and `return_value` modifiers are not applicable as a non-last-target modifier because subsequent targets are applied based on the selected records. Hence, the selected records must be `StatementExecution` objects. This also means that `type="variable"` can only be in the last `TargetElement`.

4. Cleans the final output using `_clean_output`. This step simplies the result instead of returning the full internal object.

    For example, a variable is requested.

    The internal object looks like:

    ```python
    VariableSnapshot(
        name="x",
        value=42,
        execution_id=15,
        scope_id=3,
        ...
    )
    ```

    However, the relevant information for the user would be the variable value. Hence, this step helps to return readable and relevant information to the user.


### 1. `_get_target`

Dispatches `TargetElement` to the correct handler.
* first target: `_get_target_first`
* subsequent targets: `_get_target_join`
We use `_first_target_done` to identify which handler to use.

They are handled differently because the first target is applied on the initial result set while subsequent targets relates that result set via joins.

---

`_get_target_first`:

Filters items to the requested target.

1. Filters by `type`.

2. Filters by `name` using `_apply_name_filter`.

    `_apply_name_filter`:

    `name` in `TargetElement` refers to different fields based on the `type`. This function applies the `name` filter to the correct field:
    * `branch`: `condition_str`
    * `function`: `func_full_name`
    * `variable`: `name`
        * The `name` field can contain multiple variable names that are comma-separated (e.g. `x, y`).


3. Filters by `line_number`.

    For function calls, it can either be a definition line or a call line. If the requested `line_number` matches a `func_def_line_num`, that would indicate that the requested function call is a function definition. For function definitions, the requested `line_number` refers to `func_def_line_num`.

    This distinction is required as a user can request for all function calls of a particular function definition, which requires the user to use the `func_def_line_num` to filter for.

    ```python
    def foo():  # line 1
        pass

    foo()  # line 4
    foo()  # line 5
    ```

    Using `line_number=1` obtains both function calls at lines 4 and 5. Using `line_number=4` only obtains the function call at line 4.

4. Handles `modifier`.

    For `branch_true` and `branch_false` modifiers, it applies a filter on the `condition_result` for branches.

    For `loop_iterations`, it left joins with the `exec_ctx_items` such that it only includes items from `exec_ctx_items` that are `loop_iterations` and belongs to the `loop` that we have already filtered for.


---

`_get_target_join`:

Find the target based on the current results by performing a join. The join condition pulls the previous stage out of the joined row. If the result is a `JoinResult`, then we want to pull only the previous stage out, by using the `join_idx`, which refers to the index of the latest join as all joined results can be referred to based on their corresponding `join_idx`.

It checks if the left side is a `StatementExecution` and applies the conditions from the `TargetElement`. The left side needs to be a `StatementExecution` because the subsequent target elements always refer to previous `StatementExecution`. For example, function calls in loops, variables in function calls. It doesn't make sense for other scenarios like function calls in variables.

```
loop -> loop iterations -> function calls -> variables (valid)
variables -> function calls (invalid)
function call arguments -> loop (invalid)
```

**Condition checkers:**
* `_check_stmt_type`: accepts only `RHS` with required statement type

* `_check_name_match`: applies `name` filter to correct field.

* `_check_line_number`: applies `line_number` filter. If it is referring to a function definition, applies filter on the `func_def_line_num` field.

* `_check_time_range`: ensures that `RHS` is executed within the lifetime of `LHS`. The lifetime of `LHS` is its `execution_id` to its `end_execution_id`.
    * For non-variable targets, it requires the `RHS` to fall within the execution interval of the `LHS`.
    * For variable targets, it only requires the variable snapshot to occur before the left execution ends.

* `_check_scope`: for variable targets, check that `RHS` is within the scope of `LHS`. If the `LHS` is a `FunctionCall`, use the `func_scope_id` because `scope_id` refers to the scope within which the function is called, while `func_scope_id` refers to the scope that the function creates. Other statement types are handled using `_check_time_range`.

* `_check_loop_iterations`: if the target modifier is `loop_iterations`, filters `RHS` for `LoopIteration` belonging to the `LHS`.
    * **Code Improvement**: This method seems incorrect. It should have an additional join so that we have the information of both the `LoopExecution` and `LoopIteration` similar to how `_get_target_first` handled loop iterations. The current code filter for `LoopExecution`s using `_check_stmt_type` and then try to filter for `LoopIterations` using `_check_loop_iterations` while assuming the `LHS` is the corrresponding `LoopExecution`, which is incorrect.

* `_check_branch_modifier`: applies branch condition result filter based on branch modifier.

`_get_target_first` does not use these condition checkers as these condition checkers references the `RHS` item during a join. Hence, the condition checkers are only used in the join condition.

---

**Join aliases**:

The current left side is labeled with `join_idx` and the new right side is labeled with `join_idx+1`. The first target (after joining) has alias `0`, the first join produces alias `1`, the second join produces alias `2`, and so on. This ensures that there are no name clashes in the joins and also allows us to know how to refer to results from previous stages.

---

### 2. `_apply_output_type`

Dispatches results to the corresponding method to transforms results into the requested output type.

**Code Improvement**: This should be handled by the `QueryEngine` instead, such as implementing a `count` method.


---

`_apply_count_output`:

Counts the number of rows at the deepest join level. Uses `_apply_group_by` to group rows under the same parent path.

```python
[
    JoinResult({"0": A, "1": B, "2": D}),     # row 1
    JoinResult({"0": A, "1": B, "2": None}),  # row 2
    JoinResult({"0": A, "1": C, "2": E}),     # row 3
]
```

(A, B) and (A, C) rows are grouped together respectively:
* (A, B): row 1 and 2
* (A, C): row 3

Then, all rows within the group are counted. If the row is `None` (like row 2), it will be ignored. The `None` check is done in two ways:
* check if the entire item is `None`
* for `JoinResult`, check if the row from the most recently joined table is `None`
Hence, non-matching rows are filtered out from the count.

---

`_apply_list_output`:

A list output returns generally returns the results as they are.

Variables are handled differently here to return their values instead of the entire `VariableSnapshot`. 

**Code Improvement**: It may make more sense to move this variable handling logic to `_clean_output`. But this variable handling is included here because `_apply_first_output` and `_apply_last_output` handles variables within their methods.

Variables are handled in the following cases:

* **Case 1:** joined variables (targets: ... -> variable)

    ```
    "target": [
        {
            "type": "loop",
            "id": [0],
            "line_number": 5,
            "modifier": "loop_iterations",
        },
        {"type": "variable", "id": [0], "name": "left,right"},
    ]
    ```

    The parents are grouped together and the values of each variable within the group is extracted. The variable values are sorted by their `var_id`.

    Example results: `[[0, 7, 4], [0, 7, 4, 6], [0, 7, 4, 6]]`

    **Code Improvement**: The variable name is lost and we are unable to identify which value belongs to which variable.

* **Case 2:** list of variable snapshots

    ```
    "target": [
        {"type": "variable", "id": [0], "name": "left,right"}
    ]
    ```

    Finds the variable snapshot for each variable name, finds all values. Values are not sorted.

    Example results: `[{'left': [0, 4, 6], 'right': [7]}]`

    **Code Improvement**: Might be better to sort values by `var_id`. It is not explicitly sorted as it relies on the original ordering of the variables from the `execution_context`, which is already sorted by `var_id`. But an explicit sort may be better.

---

`_apply_first_output`:

Gets the first item within the result.
* For variable joins, they are handled using `_make_variable_aggregator` to handle the variable's relation to its parent row.
* For other types, they can be handled by sorting according to the key obtained from `_make_key` and getting the minimum item.

---

`_apply_last_output`:

Gets the last item within the result. Similar to `_apply_first_output`.

---

#### Helpers

`_apply_group_by`: 

Groups the query by the `execution_id` of all join levels except the last level.

For example, if 2 joins have already been performed, the rows would look like:

```python
[
    JoinResult({"0": A, "1": B, "2": D}),
    JoinResult({"0": A, "1": B, "2": None}),
    JoinResult({"0": A, "1": C, "2": E}),
]
```

The query is grouped by the execution ids of the first 2 join aliases.

```python
query.group_by("0.execution_id", "1.execution_id")
```

---

`_make_key`: 

Returns a sorting key to identify the order of items to handle `first` and `last` outputs.

| Case Number | Is Joined Result (`join_idx > 0`) | Is Variable Target | Key      |
| ----------- | --------------------------------- | ------------------ | -------- |
| 1           | Yes                               | Yes                | `var_id` |
| 2           | Yes                               | No                 | `(execution_id, var_id)` |
| 3           | No                                | Yes                | `var_id` |
| 4           | No                                | No                 |  `(execution_id, var_id)` |


For joined results, if the item is `None`, the key returned is `-1` or `(-1, -1)` based on the key shape. This is to give the item the lowest priority.

**Code Improvement**: For non-variable target, the key is `(execution_id, var_id)`. `var_id` is unncessary here. It was originally used as a tie breaker to handle variable targets but this was later modified for variable targets to use `var_id` directly. Hence, non-variable targets should use `execution_id` as their key only.

---

`_make_picker`: 

Returns a function that decides which candidate is best relative to the parent row for variables.

For `first` output type (`before_parent=True`):
* Prefer candidates that start before the parent’s start.
* If any such candidates exist, choose the one with the largest variable key among them.
* Otherwise, choose the earliest candidate overall.

This is because we want to find the initial value of the variable, which may have been defined outside the execution we are interested in. In the future, we can consider using scopes to handle this instead of relying on the `execution_id`.

For `last` output type (`before_parent=False`):
* Prefer candidates that are inside the parent’s range.
* If any such candidates exist, choose the one with the largest variable key.
* Otherwise, choose the latest candidate overall.

This is because if no additional snapshot was taken within the parent's range, find the latest value of the variable before the parent's range. In the future, we can consider using scopes to handle this instead of relying on the `execution_id`.

---

`_make_variable_aggregator`: 

Builds an aggregator for queries whose target is a variable join.

After the target selection stage, the results will look similar to:
```python
[
    JoinResult(alias_to_items={
        '0': LoopExecution(...),
        '1': LoopIteration(...),
        '2': VariableSnapshot(name='left', ...)
    }),
    JoinResult(alias_to_items={
        '0': LoopExecution(...),
        '1': LoopIteration(...),
        '2': VariableSnapshot(name='left', ...)
    }),
    JoinResult(alias_to_items={
        '0': LoopExecution(...),
        '1': LoopIteration(...),
        '2': VariableSnapshot(name='right', ...)
    }),
]
```

The `_make_variable_aggregator` helps to collapse the rows in the same group into one row and handle multi-variable targets.

`var_names` is a list of variable names in the target. E.g. `target.name = "x,y"` -> `var_names = ["x", "y"]`. However, if there is only one variable name targeted (i.e. no commas in the target name), then `var_names` would be `None`. **Code Improvement**: Instead of using `None`, check for single/multi variable using length of `var_names`.

`pick`: filters candidates by variable name and uses `pick_for_name` to choose the best option from the candidates.

If there are multiple variable names
* picks one result per variable name,
* extracts each picked value,
* packs them into a tuple ordered by the order in which the variable names appeared,
* returns a new JoinResult containing that tuple as the joined value.
    * A new JoinResult needs to be created to store the value of the tuple. The `VariableSnapshot` is replaced with the tuple.

```python
[
    JoinResult(alias_to_items={
        '0': LoopExecution(...),
        '1': LoopIteration(...),
        '2': namespace(value=(...))
    }),
    JoinResult(alias_to_items={
        '0': LoopExecution(...),
        '1': LoopIteration(...),
        '2': namespace(value=(...))
    }),
]
```

If there is only one variable name, the candidates will have already been filtered for the variable name, so we
* picks the best matching candidate,
* returns that candidate directly.

---


### 3. `_apply_modifier`

Applies the `arguments` or `return_value` modifier. This step is performed after the `_apply_output_type` step because the output type step narrows down the rows for `first` and `last` outout types so less rows need to be processed.

It selects the `argument` or `return_type` field from the rows. 

For `arguments`, additional processing is performed using `_apply_argument_keys`. `argument_keys` is a field in the target to select specific arguments. It iterates through the arugments and extracts the required ones. The argument name is included if more than one argument is selected.


---

### 4. `_clean_output`

Converts internal objects into readable values by extracting relevant user-facing values.

The `count` output type is already clean so no further clean up is required.

**Variable Clean Up**:

When the last target type is a variable, a `name` may or may not be defined.

* Case 1: `name` is `None`

    All variables are selected. As there may be multiple different variables, the name and value of the variables are selected. If only values are selected, it would be ambiguous as to which variables the values belonged to.

* Case 2: `name` is defined.

    Selects the value only. Name is not selected. If there are multiple variables in name (e.g. `"x,y"`), it is handled in the output type handling. **Code Improvement**: There seems to be improper handling of multi variable names for `first` and `last` output types. Currently, only the first/last variable for any variable name is included, instead of first/last variable for each variable name. 

**Argument Clean Up**:

Extract the argument value if only one argument.


**Code Improvements**: 

Internal objects should be cleaned too instead of just handling variables and arguments. This should be handled by the models in the `Step Tracer` to provide a method to sterilise the object.
