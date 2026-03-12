import json
import os
import re
import matplotlib.pyplot as plt
from utilities.integrate_stress_profile import integrate_stress_profile
from itertools import cycle


class ForcePlotter:
    def __init__(self, data_filepath, thickness, force_directions):
        self.data_filepath = data_filepath
        self.thickness = thickness
        self.force_directions = force_directions
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

    def plot_forces(self, odbs_to_plot=None, force_directions_to_plot=None, save_dir_path=None):
        available_odbs = self.get_available_odbs()
        
        color_cycle = cycle(plt.cm.tab10.colors)
        color_map = {odb_name: next(color_cycle) for odb_name in available_odbs}

        linestyle_cycle = cycle(['-', '--', ':', '-.'])
        linestyle_map = {}

        if not odbs_to_plot:
            odbs_to_use = available_odbs
        else:
            odbs_to_use = [odb for odb in odbs_to_plot if odb in available_odbs]

        if not force_directions_to_plot:
            force_directions_to_use = self.force_directions
        else:
            force_directions_to_use = [var for var in force_directions_to_plot if var in self.force_directions]

        def get_odb_sort_key(odb_name):
            try:
                number = re.search(r'\d+$', odb_name)
                return int(number.group()) if number else 0
            except ValueError:
                return 0

        odbs_to_use.sort(key=get_odb_sort_key, reverse=True)

        for force_direction_name in force_directions_to_use:
            fig, ax = plt.subplots(figsize=(12, 7))
            has_data = False

            for odb_name in odbs_to_use:
                if force_direction_name not in self.data[odb_name]:
                    continue

                ext_type_list = self.data[odb_name][force_direction_name].keys()
                color = color_map.get(odb_name)

                for ext_type in ext_type_list:
                    if ext_type not in linestyle_map:
                        linestyle_map[ext_type] = next(linestyle_cycle)
                    
                    current_linestyle = linestyle_map[ext_type]
                    ext_type_data = self.data[odb_name][force_direction_name][ext_type]
                    
                    if not ext_type_data:
                        continue

                    has_data = True
                    time_values = [item['time'] for item in ext_type_data]
                    time_micro_values = [t * 1e6 for t in time_values]

                    force_values = []
                    
                    if ext_type == 'whole_surf':
                        for item in ext_type_data:
                            raw_xy_list = item['xy_datalist']
                            xy_tuples = [(d['true_distance'], d['stress']) for d in raw_xy_list]
                            
                            force = abs(integrate_stress_profile(xy_tuples, self.thickness))
                            force_values.append(force)
                    else:
                        force_values = [abs(item['RF']) for item in ext_type_data]

                    ax.plot(time_micro_values, force_values,
                            color=color,
                            linestyle=current_linestyle,
                            label=f"{odb_name} ({ext_type})")
            
            if has_data:
                ax.set_xlabel("Time (µs)")
                ax.set_ylabel("Absolute Force (N)")
                ax.set_title(f"Comparison Forces ({force_direction_name})")
                ax.legend()
                ax.grid(True)
                plt.tight_layout()
                
                if save_dir_path:
                    if not os.path.exists(save_dir_path):
                        os.makedirs(save_dir_path)
                    file_name = f"{force_direction_name}.png"
                    save_file_path = os.path.join(save_dir_path, file_name)
                    plt.savefig(save_file_path)
                    print(f"Plot saved to: {save_file_path}")
                
                plt.close(fig)
            else:
                plt.close(fig)
                print(f"No data found for direction: {force_direction_name}")


def main():
    DATA_FILE = "backend/data/data.json"
    SAVE_PLOT_DIR = os.path.dirname(DATA_FILE)
    
    FORCE_DIRECTIONS = ['S13', 'S33']
    THICKNESS = 0.02

    plotter = ForcePlotter(DATA_FILE, THICKNESS, FORCE_DIRECTIONS)

    if plotter.load_data():
        plotter.plot_forces(save_dir_path=SAVE_PLOT_DIR)


if __name__ == "__main__":
    main()