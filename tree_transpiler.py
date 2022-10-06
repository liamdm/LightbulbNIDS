from collections import OrderedDict
from typing import List, Tuple, Union

import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.tree import export_text


class CTreeGenerator:
    def __init__(self, dt:Union[List[DecisionTreeClassifier], DecisionTreeClassifier], variable_names:List[str]):
        variable_names = [f"arg{i+1}" for i in range(len(variable_names))]
        self.dt = dt # type: DecisionTreeClassifier
        self.variable_names = variable_names

    def generate_current_level(self, r, depth) -> Tuple[str, List[str]]:
        r_lines = r.splitlines(keepends=False)

        indent = " " * (depth * 2)

        if len(r_lines) == 1:
            assert ("class" in r_lines[0])
            classification = r_lines[0]
            classification = classification.strip("|- ")
            classification = classification.replace("class: ", "return ").replace("1.0", "true").replace("0.0", "false")
            classification += ";"
            return indent + classification + "\n", []

        all_depths = []
        for l_i, l in enumerate(r.splitlines(keepends=False)):
            l_depth = l.count("|")

            all_depths.append({
                "Line": l_i,
                "Depth": l_depth,
                "Text": l
            })

        all_depths = pd.DataFrame(all_depths)

        target_depth = depth + 1

        started_capture = False
        current_group = None

        groups = OrderedDict()

        outer_condition = None

        vars_l = []

        for row_i in range(len(all_depths)):
            data = all_depths.iloc[row_i]

            line = data["Line"]
            line_depth = data["Depth"]
            text = data["Text"]

            if line_depth == target_depth:
                if not started_capture:
                    started_capture = True
                    current_group = (line, line_depth, text)

                    l_data = text.strip("|- ").split(" ")

                    feature_name = l_data[0]
                    operator = l_data[1]
                    threshold = float(l_data[2])

                    c_name = self.get_real_variable_name(feature_name) #column_names_clean[feature_id]
                    vars_l.append((feature_name, c_name))

                    if "[" in c_name:
                        # binary
                        if ">" in operator:
                            outer_condition = f"{c_name}"
                        else:
                            outer_condition = f"!{c_name}"
                    else:
                        outer_condition = f"{c_name} {operator} {threshold}"

                else:
                    current_group = (line, line_depth, text)
                groups[current_group] = []
            else:
                if started_capture:
                    groups[current_group].append((line, line_depth, text))

        assert (len(groups) == 2)

        groups2 = []

        for (_, _, group_name), items in groups.items():
            all_lines = "\n".join([l for _, _, l in items])
            groups2.append(all_lines)

        groups = groups2

        text_1, vars_1 = self.generate_current_level(groups[0], target_depth)
        text_2, vars_2 = self.generate_current_level(groups[1], target_depth)

        sb = ""
        sb += "  " + indent + f"if({outer_condition}){{\n"
        sb += "  " + text_1
        sb += "  " + indent + "} else {\n"
        sb += "  " + text_2
        sb += "  " + indent + "}\n"

        return sb, list(sorted(list(set(vars_l + vars_1 + vars_2))))

    def get_real_variable_name(self, n:str):
        return n
        # name = ""
        # for i, v in enumerate(n.split("_")):
        #     c0 = v[0]
        #     c0 = c0.upper() if i > 0 else c0.lower()
        #     name += c0 + v[1:].lower()
        # return name

    def generate(self):
        r = export_text(self.dt, decimals=5, feature_names=self.variable_names, max_depth=20)
        tree_code, allocated_variables = self.generate_current_level(r, 0)
        return tree_code
