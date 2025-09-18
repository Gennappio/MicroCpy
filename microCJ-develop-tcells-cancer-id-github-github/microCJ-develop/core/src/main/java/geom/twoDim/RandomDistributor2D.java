package geom.twoDim;

import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

public class RandomDistributor2D extends Distributor2D {
	private final Random r = ThreadLocalRandom.current();

	public RandomDistributor2D(double gap, boolean cache) {
		super(gap, cache);
	}

	@Override
	public void repopulate() {
		super.repopulate();

		while(getLocations().size() != getTotal()) {
			var newLocation = locateEmptySpotNextTo(getLocations().get(r.nextInt(getLocations().size())));
			if (newLocation == null) {
				newLocation = getArbitraryPointNextTo(getLocations().get(0));
				shove();
			}
			getLocations().add(newLocation);
		}
		shove();
	}

	@Override
	public Point2D locateEmptySpotNextTo(Point2D location) {
		Point2D newPoint = null;
		double period = Math.PI*2/100;

		for (int i = 0; i < 10000; i++) {
			double angle = period * i;
			Point2D possiblePoint = pointAtArc(location, angle);
			boolean empty = getLocations().parallelStream().allMatch(point -> point.distance(possiblePoint) >= getGap());

			if (empty) {
				newPoint = possiblePoint;
				break;
			}
		}

		return newPoint;
	}

	@Override
	public Point2D getArbitraryPointNextTo(Point2D origin) {
		double angle = r.nextDouble() * Math.PI * 2;
		return pointAtArc(origin, angle);
	}

	private Point2D pointAtArc(Point2D origin, double angle) {
		double x = Math.cos(angle) * getGap();
		double y = Math.sin(angle) * getGap();
		return origin.add(x, y);
	}

	@Override
	public void shove() {
		for (int t = 0; t < 10; t++) { //todo replace this with a check for any 2 cells touching
			for (int i = 0; i < getLocations().size(); i++) {
				Point2D ic = getLocations().get(i);
				double deltaX = 0;
				double deltaY = 0;
				boolean moved = false;

				for (int j = 0; j < getLocations().size(); j++) {
					Point2D jc = getLocations().get(j);
					double distance = ic.distance(jc);
					double delta = getGap() - distance;

					if (delta > 0 && i != j) {
						moved = true;
						deltaX += delta * (jc.getX() - ic.getX()) / distance;
						deltaY += delta * (jc.getY() - ic.getY()) / distance;
					}
				}
				if (moved) {
					getLocations().set(i, ic.subtract(deltaX, deltaY));
				}
			}
		}
	}
}
