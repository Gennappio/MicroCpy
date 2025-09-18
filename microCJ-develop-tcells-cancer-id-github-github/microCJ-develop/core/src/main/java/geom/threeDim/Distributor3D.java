package geom.threeDim;
/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */

import geom.Distributor;
import geom.Point;
import geom.twoDim.Point2D;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.apache.commons.csv.CSVRecord;

import java.io.*;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public abstract class Distributor3D implements Distributor {
	private final List<Point3D> locations = new ArrayList<>();
	private final double gap;
	private final boolean cache;
	private int total;
	private String cacheFileName = getClass().getSimpleName() + "-cache.csv";

	public Distributor3D(double gap, boolean cache) {
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
						locations.add(new Point3D(Double.parseDouble(record.get("x")),
								Double.parseDouble(record.get("y")),
								Double.parseDouble(record.get("z"))));
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
		if(getLocations().isEmpty()) getLocations().add(Point3D.ZERO); //it may not be empty due to a partial cache loading.
	}

	@Override
	public void setTotal(int total) {
		this.total = total;
	}

	@Override
	public int getTotal() {
		return total;
	}

	@Override
	public Point locateEmptySpotNextTo(Point location) {
		return locateEmptySpotNextTo((Point3D) location);
	}

	public abstract Point3D locateEmptySpotNextTo(Point3D location);

	/**
	 * Returns an arbitrary point at a gap distance from the origin, without a guarantee that said point will be out of gap distance from other points.
	 *
	 * @param origin the center of the circle
	 * @return an arbitrary point at a gap distance from the origin
	 */
	public abstract Point3D getArbitraryPointNextTo(Point3D origin);

	public List<Point3D> getLocations() {
		return locations;
	}

	double getGap() {
		return gap;
	}

	@Override
	public void remove(Point point) {
		var point3d = (Point3D) point;
		getLocations().remove(point3d);
	}

	public void cache() {
		try (CSVPrinter printer = new CSVPrinter(new FileWriter(getTotal() + "_" + cacheFileName), CSVFormat.DEFAULT)) {
			printer.printRecord("x", "y", "z");
			for (Point3D location : getLocations())
				printer.printRecord(location.getX(), location.getY(), location.getZ());
		} catch (IOException ex) {
			ex.printStackTrace();
		}
	}
}