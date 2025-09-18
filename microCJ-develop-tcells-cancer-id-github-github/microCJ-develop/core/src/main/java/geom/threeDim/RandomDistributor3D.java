package geom.threeDim;
/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */

import geom.twoDim.Point2D;

import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

public class RandomDistributor3D extends Distributor3D {
	private final Random r = ThreadLocalRandom.current();

	public RandomDistributor3D(double gap, boolean cache) {
		super(gap, cache);
	}

	@Override
	public void repopulate() {
		super.repopulate();
		while(getLocations().size() != getTotal()){
			getLocations().add(getArbitraryPointNextTo(Point3D.ZERO));
			shove();
		}
	}

	@Override
	public Point3D locateEmptySpotNextTo(Point3D location) {
		Point3D newPoint = null;
		for (int i = 0; i < 10000; i++) {
			Point3D rndPoint = getArbitraryPointNextTo(location);
			boolean empty = getLocations().stream().allMatch(point -> point.distance(rndPoint) >= getGap());

			if (empty) {
				newPoint = rndPoint;
				break;
			}
		}

		return newPoint;
	}

	@Override
	public Point3D getArbitraryPointNextTo(Point3D origin) {
		//from https://math.stackexchange.com/a/1585996
		double[] rndArray = new double[3];
		double rndSqrSum = 0;

		for (int i = 0; i < 3; i++) {
			rndArray[i] = r.nextGaussian();
			rndSqrSum += rndArray[i] * rndArray[i];
		}

		double factor = getGap() / Math.sqrt(rndSqrSum);
		Point3D direction = new Point3D(rndArray[0], rndArray[1], rndArray[2]);
		return origin.add(direction.multiply(factor));
	}

	@Override
	public void shove() {
		for (int t = 0; t <10; t++) {
			for (int i = 0; i < getLocations().size(); i++) {
				Point3D ic = getLocations().get(i);
				double deltaX = 0;
				double deltaY = 0;
				double deltaZ = 0;
				boolean moved = false;

				for (int j = 0; j < getLocations().size(); j++) {
					Point3D jc = getLocations().get(j);

					double distance = ic.distance(jc);
					double delta = getGap() - distance;

					if (delta > 0 && i != j) {
						moved = true;
						deltaX += delta * (jc.getX() - ic.getX()) / distance;
						deltaY += delta * (jc.getY() - ic.getY()) / distance;
						deltaZ += delta * (jc.getZ() - ic.getZ()) / distance;
					}
				}
				if (moved) {
					getLocations().set(i, ic.subtract(deltaX, deltaY, deltaZ));
				}
			}
		}
	}
}