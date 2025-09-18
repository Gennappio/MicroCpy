/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package geom.threeDim;

import geom.twoDim.Point2D;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

/**
 * @author Pedro Victori
 */
public class HexagonalDistributor3D extends Distributor3D {
	private static final Point3D[] regularIntervals = {
			new Point3D(1, 0,0),
			new Point3D(0.5, -1,0),
			new Point3D(-0.5, -1,0),
			new Point3D(-1, 0,0),
			new Point3D(-0.5, 1,0),
			new Point3D(0.5, 1,0),
			new Point3D(0.5, 0.5,1),
			new Point3D(-0.5, 0.5,1),
			new Point3D(0, -0.5,1),
			new Point3D(0.5, 0.5,-1),
			new Point3D(-0.5, 0.5,-1),
			new Point3D(0, -0.5,-1)
	};



	public HexagonalDistributor3D(double gap, boolean cache) {
		super(gap, cache);
	}

	@Override
	public void populate(int n) {
		setTotal(n);
		repopulate(); //this class will never cache the positions
	}

	@Override
	public void repopulate() {
		Point3D[] modRegularIntervals = new Point3D[12];
		for (int i = 0; i < 12; i++) {
			modRegularIntervals[i] = regularIntervals[i].multiply(getGap());
		}

		getLocations().add(Point3D.ZERO);
		Random rand = ThreadLocalRandom.current();
		List<Point3D> workingList = new ArrayList<>(getLocations());

		for (int i = 1; i < getTotal(); ) {
			int r = rand.nextInt(12);
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
