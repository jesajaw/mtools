from typing import Tuple, List, Optional

def split_data(data)-> Tuple[int, int, List[float], List[float], Optional[List[float]]]:
    if not data or isinstance(data[0], (str, int, float)):
        return len(data), 1, [float(p) for p in data], None, None
        
    dimension = len(data[0])
    return (len(data), dimension,
        [float(p[0]) for p in data],
        [float(p[1]) for p in data] if dimension > 1 else list(range(len(data))),
        [float(p[2]) for p in data] if dimension > 2 else None,)

def dataset_to_points(dataset):
    if "y" not in dataset.axes and "y" not in dataset.data:
        return dataset.get("x").values
    cols = [dataset.get(n).values for n in ("x", "y", "z") if n in dataset.axes or n in dataset.data]
    return list(zip(*cols))
    