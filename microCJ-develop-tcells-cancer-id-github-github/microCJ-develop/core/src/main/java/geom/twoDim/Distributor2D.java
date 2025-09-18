package geom.twoDim;

import geom.Distributor;
import geom.Point;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.apache.commons.csv.CSVRecord;

import java.io.*;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public abstract class Distributor2D implements Distributor {
	private final List<Point2D> locations = new ArrayList<>();
	private final double gap;
	private final boolean cache;
	private String cacheFileName = getClass().getSimpleName() + "-cache.csv";
	private int total;

	public Distributor2D(double gap, boolean cache) {
		this.gap = gap;
		this.cache = cache;
	}

	@Override
	public void populate(int n) {
		total = n;
		if(cache){
			File dir = new File(".");
			var files = dir.listFiles();

			var positionsInMatchingFileOptional = Arrays.stream(files)
					.filter(file -> file.getName().endsWith(cacheFileName))
					.mapToInt(file -> {
						String[] parts = file.getName().split("_");
						return Integer.parseInt(parts[0]);})//the number of positions this file contains
					.filter(nCache -> nCache <= n) //we need a cache with fewer positions (to build upon) or the same number.
					.max();

			if(positionsInMatchingFileOptional.isPresent()) { //read cache and store it in locations
				int positionsInMatchingFile = positionsInMatchingFileOptional.getAsInt();
				File cacheFile = new File(positionsInMatchingFile + "_" + cacheFileName);
				Reader in = null;
				try {
					in = new FileReader(cacheFile);
				} catch (FileNotFoundException e) {
					e.printStackTrace();
				}
				try {
					var records = CSVFormat.DEFAULT.withFirstRecordAsHeader().parse(in);
					for (CSVRecord record : records) {
						locations.add(new Point2D(Double.parseDouble(record.get("x")), Double.parseDouble(record.get("y"))));
					}
					if(positionsInMatchingFile < n){ //complete with new positions as needed
						repopulate();
						cache();
					}
				} catch (IOException e) {
					e.printStackTrace();
				}
			} else {
				repopulate();
				cache();
			}
		} else repopulate();
	}

	void repopulate(){
		if(getLocations().isEmpty()) getLocations().add(Point2D.ZERO); //it may not be empty due to a partial cache loading.
	}

	@Override
	public void setTotal(int total) {
		this.total = total;
	}

	@Override
	public int getTotal() {
		return total;
	}

	public abstract Point2D locateEmptySpotNextTo(Point2D location);

	/**
	 * Returns an arbitrary point at a gap distance from the origin, without a guarantee that said point will be out of gap distance from other points.
	 *
	 * @param origin the center of the circle
	 * @return an arbitrary point at a gap distance from the origin
	 */
	public abstract Point2D getArbitraryPointNextTo(Point2D origin);

	@Override
	public Point locateEmptySpotNextTo(Point location) {
		return locateEmptySpotNextTo((Point2D) location);
	}

	public List<Point2D> getLocations() {
		return locations;
	}

	double getGap() {
		return gap;
	}

	@Override
	public void remove(Point point) {
		var point2d = (Point2D) point;
		getLocations().remove(point2d);
	}

	@Override
	public void cache() {
		try (CSVPrinter printer = new CSVPrinter(new FileWriter(getTotal() + "_" + cacheFileName), CSVFormat.DEFAULT)) {
			printer.printRecord("x", "y");
			for (Point2D location : getLocations()) printer.printRecord(location.getX(), location.getY());
		} catch (IOException ex) {
			ex.printStackTrace();
		}
	}
}
