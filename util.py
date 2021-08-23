from datetime import datetime as dt
import time


def get_entry(record, column_name, columns):
    i = columns.index(column_name)
    return record[i]


def get_entries_across(record, column_names, columns):
    result = []
    for value, column in zip(record, columns):
        if column in column_names:
            result.append(value)
    return result


def get_entries(records, column_name, columns):
    i = columns.index(column_name)
    return [list(record)[i] for record in records]


def set_entry(record, value, column_name, columns):
    i = columns.index(column_name)
    record[i] = value


def set_entries_across(record, map_column_name_to_value, columns):
    for column_name, value in map_column_name_to_value.items():
        i = columns.index(column_name)
        record[i] = value


def set_entries(records, values, column_name, columns):
    i = columns.index(column_name)
    for (record, value) in zip(records, values):
        record[i] = value


def truncate_values(values, header):
    max_length = len(header)
    return [record[:max_length] for record in values]


def now():
    return str(dt.now())


def get_assignment(assignments, assignment):
    for i, asmt in enumerate(assignments):
        if assignment == asmt["name"]:
            return assignments[i]

    raise KeyError(f"Assignment {assignment} does not exist")


def get_questions(questions, question):
    ans = []

    for q in questions:
        try:
            colon = q.index(":")
            paren = q.index("(")
        except ValueError:
            continue

        if q[colon + 2 : paren - 1].startswith(question):
            ans.append(q)

    if len(ans) == 0:
        raise KeyError(f"No matching question {question} found")

    return ans


def get_question_ta(q_eval):
    for key, value in q_eval["rubric_items"].items():
        if key.startswith("Grader") and value:
            try:
                op = key.index("(")
            except ValueError:
                continue

            return key[op + 1 : op + 3]

    return None


def rate_limit(i, entries_per_batch, wait_time=100):
    if i % entries_per_batch == entries_per_batch - 1:
        time.sleep(wait_time)
