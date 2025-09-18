/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package geom.threeDim;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

/**
 * @author Pedro Victori
 */
public class SquareDistributor3D extends Distributor3D {
	private static final Point3D[] regularIntervals;

	static { //generate all 18 directions to generate a new, touching cell
		List<Point3D> points = new ArrayList<>();
		points.add(Point3D.ZERO);
		points.add(new Point3D(-1, -1, 0));
		points.add(new Point3D(-1, 0, 0));
		points.add(new Point3D(-1, 1, 0));
		points.add(new Point3D(0, -1, 0));
		points.add(new Point3D(0, 1, 0));
		points.add(new Point3D(1, -1, 0));
		points.add(new Point3D(1, 0, 0));
		points.add(new Point3D(1, 1, 0));

		//for concurrent modification
		List<Point3D> pointsCopy = new ArrayList<>(points);

		//z+-10
		for (Point3D point : points) {
			Point3D zFactor = new Point3D(0, 0, 1);
			pointsCopy.add(point.add(zFactor));
			pointsCopy.add(point.add(zFactor.multiply(-1)));
		}

		//remove point zero and corners +-10
		pointsCopy.remove(Point3D.ZERO);
		points.addAll(pointsCopy);
		for (Point3D point : points) {
			if (Math.abs(point.getX()) == 1 && Math.abs(point.getY()) == 1 && Math.abs(point.getZ()) == 1) {
				pointsCopy.remove(point);
			}
		}
		regularIntervals = pointsCopy.toArray(new Point3D[0]);
	}

	public SquareDistributor3D(double gap, boolean cache) {
		super(gap, cache);
	}

	@Override
	public void populate(int n) {
		setTotal(n);
		repopulate(); //this class will never cache the positions
	}

	@Override
	public void repopulate() {
		Point3D[] modRegularIntervals = new Point3D[18];
		for (int i = 0; i < 18; i++) {
			modRegularIntervals[i] = regularIntervals[i].multiply(getGap());
		}

		getLocations().add(Point3D.ZERO);
		Random rand = ThreadLocalRandom.current();
		List<Point3D> workingList = new ArrayList<>(getLocations());

		for (int i = 1; i < getTotal(); ) {
			int r = rand.nextInt(18);
			int s = rand.nextInt(workingList.size());
			Point3D element = workingList.get(s).add(modRegularIntervals[r]);
			if (!getLocations().contains(element)) { //todo replace this with shoving
				i++;
				getLocations().add(element);
				workingList.add(element);
			}
		}
	}

	@Override
	public Point3D locateEmptySpotNextTo(Point3D location) {
		for (Point3D interval : regularIntervals) {
			Point3D possibleEmptySpot = location.add(interval.multiply(getGap()));
			if (!getLocations().contains(possibleEmptySpot)) return possibleEmptySpot;
		}
		return null;
	}

	@Override
	public Point3D getArbitraryPointNextTo(Point3D origin) {
		return null; //todo implement
	}

	@Override
	public void shove() {
		//todo implement
	}
}
