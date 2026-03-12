import json
import os
import matplotlib.pyplot as plt
from itertools import cycle


class StressProfilePlotter:
    def __init__(self, data_filepath):
        self.data_filepath = data_filepath
        self.data = None

    def load_data(self):
        if not os.path.exists(self.data_filepath):
            print(f"File not found: {self.data_filepath}")
            return False
            
        with open(self.data_filepath, 'r') as f:
            self.data = json.load(f)
        return True

    def get_available_odbs(self):
        if self.data:
            return list(self.data.keys())
        return []

    @staticmethod
    def _sorted_frame_keys(step_data):
        def parse_key(frame_key):
            try:
                return int(frame_key)
            except ValueError:
                return float(frame_key)

        return sorted(step_data.keys(), key=parse_key)

    def _get_default_odb_and_field(self, odb_name=None, field_name=None):
        available_odbs = self.get_available_odbs()
        if not available_odbs:
            return None, None

        selected_odb = odb_name if odb_name in self.data else available_odbs[0]
        fields = list(self.data[selected_odb].keys())
        if not fields:
            return selected_odb, None

        selected_field = field_name if field_name in self.data[selected_odb] else fields[0]
        return selected_odb, selected_field

    def _extract_step_profile(self, step_data, profile_keyword, frame_selector="last"):
        frame_keys = self._sorted_frame_keys(step_data)
        if not frame_keys:
            return None

        frame_key = frame_keys[-1] if frame_selector == "last" else frame_keys[0]
        frame_data = step_data[frame_key]

        matching_paths = [
            path_name for path_name in frame_data.keys()
            if profile_keyword.lower() in path_name.lower()
        ]
        if not matching_paths:
            return None

        path_name = sorted(matching_paths)[0]
        payload = frame_data[path_name]
        if "data" not in payload:
            return None

        distances = [point["true_distance"] for point in payload["data"]]
        stresses = [point["stress"] for point in payload["data"]]

        return {
            "frame": frame_key,
            "path_name": path_name,
            "distances": distances,
            "stresses": stresses,
        }

    def _plot_profile_by_steps(
        self,
        odb_name,
        field_name,
        profile_keyword,
        title_suffix,
        save_dir_path,
        save_plot=False,
        frame_selector="last"
    ):
        step_map = self.data[odb_name][field_name]
        if not step_map:
            print("No step data found for {} / {}".format(odb_name, field_name))
            return

        color_cycle = cycle(plt.cm.tab10.colors)
        fig, ax = plt.subplots(figsize=(12, 7))
        has_data = False

        for step_name in sorted(step_map.keys()):
            step_data = step_map[step_name]
            profile = self._extract_step_profile(step_data, profile_keyword, frame_selector)
            if not profile:
                continue

            has_data = True
            ax.plot(
                profile["distances"],
                profile["stresses"],
                color=next(color_cycle),
                linewidth=1.8,
                label="{} (frame={}, path={})".format(
                    step_name, profile["frame"], profile["path_name"]
                )
            )

        if not has_data:
            plt.close(fig)
            print("No '{}' profiles found for {} / {}".format(
                profile_keyword, odb_name, field_name
            ))
            return

        ax.set_xlabel("True Distance")
        ax.set_ylabel("Stress")
        ax.set_title("{} - {} ({})".format(odb_name, title_suffix, field_name))
        ax.grid(True)
        ax.legend()
        plt.tight_layout()

        # Conditionally save the plot
        if save_plot and save_dir_path:
            if not os.path.exists(save_dir_path):
                os.makedirs(save_dir_path)
            file_name = "{}_{}_{}.png".format(odb_name, field_name, profile_keyword)
            save_file_path = os.path.join(save_dir_path, file_name)
            plt.savefig(save_file_path)
            print("Plot saved to: {}".format(save_file_path))

        # Notice that plt.close(fig) was removed here so the figures stay active

    def plot_step_stress_profiles(
        self,
        odb_name=None,
        field_name=None,
        save_dir_path=None,
        save_plot=False,
        frame_selector="last"
    ):
        selected_odb, selected_field = self._get_default_odb_and_field(
            odb_name=odb_name,
            field_name=field_name
        )

        if not selected_odb or not selected_field:
            print("No valid ODB/field found in JSON data.")
            return

        self._plot_profile_by_steps(
            odb_name=selected_odb,
            field_name=selected_field,
            profile_keyword="surface",
            title_suffix="Surface Stress Profile Across Steps",
            save_dir_path=save_dir_path,
            save_plot=save_plot,
            frame_selector=frame_selector
        )
        self._plot_profile_by_steps(
            odb_name=selected_odb,
            field_name=selected_field,
            profile_keyword="depth",
            title_suffix="Depth Stress Profile Across Steps",
            save_dir_path=save_dir_path,
            save_plot=save_plot,
            frame_selector=frame_selector
        )

        # Always show all generated plots at the end
        plt.show()


def main():
    DATA_FILE = "backend/data/data.json"
    SAVE_PLOT_DIR = os.path.dirname(DATA_FILE)

    plotter = StressProfilePlotter(DATA_FILE)

    if plotter.load_data():
        plotter.plot_step_stress_profiles(
            save_dir_path=SAVE_PLOT_DIR,
            save_plot=True,  # Set this to False if you only want to view the plots
            frame_selector="last"
        )


if __name__ == "__main__":
    main()