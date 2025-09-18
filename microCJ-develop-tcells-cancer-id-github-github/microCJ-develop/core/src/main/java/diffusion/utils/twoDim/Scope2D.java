package diffusion.utils.twoDim;

import geom.twoDim.Point2D;

import java.util.Iterator;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

public class Scope2D implements Iterable<Position2D> {
	private final int max;
	private Position2D center;

	public Scope2D(int max) {
		this.max = max;
	}

	public int getMax() {
		return max;
	}

	private Position2D getCenterVoxel() {
		if (center == null) {
			int half = max / 2;
			center = new Position2D(half, half, this);
		}
		return center;
	}

	/**
	 * Converts 2D coordinates to a position index within this Scope.
	 *
	 * @param point     the {@code Point2D} instance to be converted.
	 * @param voxelSize the voxel size in the same units than the supplied 3D coordinates.
	 * @return a {@code Position2D} representing the xyz index within this Scope
	 * @throws IllegalArgumentException if the given Point would be outside the matrix
	 */
	public Position2D pointToPosition(Point2D point, double voxelSize) throws IllegalArgumentException {
		//divide by 10 to floor (48/10 will be 4, -35/10 will be -3)
		int i = (int) (point.getX() / voxelSize);
		int j = (int) (point.getY() / voxelSize);

		//the center of the matrix is max/2,max/2, while the center coordinate is 0,0. Add calculated indexes to the center voxel indexes.
		i += getCenterVoxel().getI();
		j += getCenterVoxel().getJ();

		if (i < 0 || i > max || j < 0 || j > max)
			throw new IllegalArgumentException("The given coordinates are outside the 3D matrix");
		return new Position2D(i, j, this);
	}

	/**
	 * Converts a position index within this dimension to a set of 2D coordinates
	 *
	 * @param voxel     the {@code Position2D} instance to be converted.
	 * @param voxelSize the voxel size in the same units than the desired 2D coordinates.
	 * @return a {@code Point2D} representing the 2D coordinates.
	 */
	public Point2D positionToPoint(Position2D voxel, int voxelSize) {
		//the center of the matrix is max/2,max/2,max/2, while the center coordinate is 0,0,0.
		int x = voxelSize * (voxel.getI() - getCenterVoxel().getI());
		int y = voxelSize * (voxel.getJ() - getCenterVoxel().getJ());

		return new Point2D(x, y);
	}

	@Override
	public Iterator<Position2D> iterator() {
		return new Iterator<>() {
			private final Position2D pos = new Position2D(0, 0, Scope2D.this);

			@Override
			public boolean hasNext() {
				return !pos.isAtMax();
			}

			@Override
			public Position2D next() {
				Position2D next = new Position2D(pos);
				pos.increment();
				return next;
			}
		};
	}

	public Stream<Position2D> stream() {
		return StreamSupport.stream(spliterator(), false);
	}
}
