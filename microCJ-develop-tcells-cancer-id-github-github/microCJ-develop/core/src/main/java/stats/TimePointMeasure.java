package stats;

import java.util.List;
import java.util.Map;

public record TimePointMeasure(Map<String, List<String>> measure) { //each list is a column, the map keys are the column names
}
