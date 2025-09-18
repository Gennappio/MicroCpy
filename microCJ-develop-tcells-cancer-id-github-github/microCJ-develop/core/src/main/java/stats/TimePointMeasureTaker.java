package stats;

import core.World;

@FunctionalInterface
interface TimePointMeasureTaker {
	TimePointMeasure take(World world);
}
