package geom.twoDim;

import java.util.List;

public enum DistributionType {
	SQUARE(List.of(
			new Point2D(1, 0),
			new Point2D(1, -1),
			new Point2D(0, -1),
			new Point2D(-1, -1),
			new Point2D(-1, 0),
			new Point2D(-1, 1),
			new Point2D(0, 1),
			new Point2D(1, 1))),
	HEXAGONAL(List.of(
			new Point2D(1, 0),
			new Point2D(0.5, -1),
			new Point2D(-0.5, -1),
			new Point2D(-1, 0),
			new Point2D(-0.5, 1),
			new Point2D(0.5, 1)));

	private final List<Point2D> directions;

	DistributionType(List<Point2D> directions) {
		this.directions = directions;
	}

	public List<Point2D> getDirections() {
		return directions;
	}
}
