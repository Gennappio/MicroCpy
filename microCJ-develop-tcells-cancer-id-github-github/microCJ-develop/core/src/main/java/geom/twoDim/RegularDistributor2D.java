package geom.twoDim;

import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

public class RegularDistributor2D extends Distributor2D { //todo consider making this an enum if shove() is generalisable
	private final List<Point2D> directions;

	public RegularDistributor2D(double gap, boolean cache, DistributionType type) {
		super(gap, cache);
		directions = type.getDirections().stream().map(point2D -> point2D.multiply(gap)).collect(Collectors.toList());
	}

	@Override
	public void populate(int n) {
		setTotal(n);
 		repopulate(); //this class will never cache the positions
	}

	@Override
	public void repopulate() {
		super.repopulate();
		Random r = ThreadLocalRandom.current();
		List<Point2D> workingList = new ArrayList<>(getLocations());

		for (int i = 1; i < getTotal(); ) {
			int originIndex = r.nextInt(workingList.size());
			Point2D element = locateEmptySpotNextTo(workingList.get(originIndex));
			if (element != null) {
				i++;
				getLocations().add(element);
				workingList.add(element);
			}
		}
	}

	@Override
	public void shove() {
		boolean anyOverlap = true;
		while(anyOverlap){
			anyOverlap = false;
			for (int i = 0; i < getLocations().size(); i++) {
				Point2D ic = getLocations().get(i);

				for (int j = 0; j < getLocations().size(); j++) {
					Point2D jc = getLocations().get(j);
					double distance = ic.distance(jc);
					if(distance == 0 && i != j){
						anyOverlap = true;
						var emptySpot = locateEmptySpotNextTo(ic);
						getLocations().set(i, Objects.requireNonNullElse(emptySpot, getArbitraryPointNextTo(ic)));
						break;
					}
				}
			}
		}
	}

	@Override
	public Point2D locateEmptySpotNextTo(Point2D location) {
		Collections.shuffle(directions);
		for (Point2D direction : directions) {
			Point2D possibleEmptySpot = location.add(direction);
			if (!getLocations().contains(possibleEmptySpot)) return possibleEmptySpot;
		}

		return null;
	}

	@Override
	public Point2D getArbitraryPointNextTo(Point2D origin) {
		Collections.shuffle(directions);
		return origin.add(directions.get(0));
	}
}
