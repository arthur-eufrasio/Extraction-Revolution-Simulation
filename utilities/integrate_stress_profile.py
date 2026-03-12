def integrate_stress_profile(data_list, thickness):
    total_integral = 0.0

    for i in range(len(data_list) - 1):
        point1 = data_list[i]
        point2 = data_list[i + 1]

        x1 = point1["true_distance"]
        x2 = point2["true_distance"]
        
        y1 = point1["stress"]
        y2 = point2["stress"]

        height = x2 - x1
        average_stress = (y1 + y2) / 2.0
        
        trapezoid_area = average_stress * height * thickness
        total_integral += trapezoid_area

    return total_integral
