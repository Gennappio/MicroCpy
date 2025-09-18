package diffusion.utils.threeDim;

import geom.threeDim.Point3D;

import java.util.Iterator;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

public class Scope implements Iterable<Position3D>{
	private final int max;
	private Position3D center;

	public Scope(int max) {
		this.max = max;
	}

	public int getMax() {
		return max;
	}

	private Position3D getCenterVoxel() {
		if(center == null){
			int half = max/2;
			center = new Position3D(half,half,half, this);
		}
		return center;
	}

	/**
	 * Converts 3D coordinates to a position index within this Scope.
	 *
	 * @param point     the {@code Point3D} instance to be converted.
	 * @param voxelSize the voxel size in the same units than the supplied 3D coordinates.
	 * @return a {@code Position3D} representing the xyz index within this Scope
	 * @throws IllegalArgumentException if the given Point would be outside the matrix
	 */
	public Position3D pointToPosition(Point3D point, double voxelSize) throws IllegalArgumentException {
		//divide by 10 to floor (48/10 will be 4, -35/10 will be -3)
		int i = (int) (point.getX() / voxelSize);
		int j = (int) (point.getY() / voxelSize);
		int k = (int) (point.getZ() / voxelSize);

		//the center of the matrix is max/2,max/2,max/2, while the center coordinate is 0,0,0. Add calculated indexes to the center voxel indexes.
		i += getCenterVoxel().getI();
		j += getCenterVoxel().getJ();
		k += getCenterVoxel().getK();

		if(i < 0 || i > max || j < 0 || j > max || k < 0 || k > max)
			throw new IllegalArgumentException("The given coordinates are outside the 3D matrix");
		return new Position3D(i, j, k, this);
	}

	/**
	 * Converts a position index within this dimension to a set of 3D coordinates
	 *
	 * @param voxel     the {@code Position3D} instance to be converted.
	 * @param voxelSize the voxel size in the same units than the desired 3D coordinates.
	 * @return a {@code Point3D} representing the 3D coordinates.
	 */
	public Point3D positionToPoint(Position3D voxel, int voxelSize) {
		//the center of the matrix is max/2,max/2,max/2, while the center coordinate is 0,0,0.
		int x = voxelSize * (voxel.getI() - getCenterVoxel().getI());
		int y = voxelSize * (voxel.getJ() - getCenterVoxel().getJ());
		int z = voxelSize * (voxel.getK() - getCenterVoxel().getK());

		return new Point3D(x, y, z);
	}

	@Override
	public Iterator<Position3D> iterator() {
		return new Iterator<>() {
			private final Position3D pos = new Position3D(0, 0, 0, Scope.this);

			@Override
			public boolean hasNext() {
				return !pos.isAtMax();
			}

			@Override
			public Position3D next() {
				Position3D next = new Position3D(pos);
				pos.increment();
				return next;
			}
		};
	}

	public Stream<Position3D> stream() {
		return StreamSupport.stream(spliterator(), false);
	}
}
