package geom;

import core.Cell;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;

import java.io.FileWriter;
import java.io.IOException;
import java.time.LocalDate;

public interface Distributor {
	void populate(int n);

	void shove();

	void setTotal(int total);

	int getTotal();

	/**
	 * Locates point at a gap distance next to the origin such as the new point is placed at that minimum given distance from any other point in the set.
	 * @param location The origin point
	 * @return a point at an empty location.
	 */
	Point locateEmptySpotNextTo(Point location);

	void remove(Point point);

	void cache();
}
