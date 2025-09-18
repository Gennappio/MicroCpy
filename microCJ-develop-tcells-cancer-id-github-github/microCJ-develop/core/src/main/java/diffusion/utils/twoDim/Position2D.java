package diffusion.utils.twoDim;

public class Position2D {
	private final Scope2D scope;
	private int i;
	private int j;
	/**
	 * Cache the hash code to make computing hashes faster.
	 */
	private int hash = 0;

	Position2D(int i, int j, Scope2D scope) {
		this.i = i;
		this.j = j;
		this.scope = scope;
	}

	Position2D(Position2D pos) {
		this.i = pos.i;
		this.j = pos.j;
		this.hash = pos.hash;
		this.scope = pos.getScope();
	}

	private static int getSmallest(int[] numbers) {
		int smallest = numbers[0];
		for (int number : numbers) {
			if (number < smallest) smallest = number;
		}
		return smallest;
	}

	void increment() {
		int max = scope.getMax();
		j++;
		if (j == max) {
			j = 0;
			i++;
			if (i > max) {
				throw new IndexOutOfBoundsException();
			}
		}
		hash = 0; //cause hash to be recomputed after modification
	}

	boolean isAtMax() {
		int max = scope.getMax();
		return i >= max;
	}

	/**
	 * Whether the current position is at the boundaries of the 2D matrix, that is, at 0 or at the maximum value in any axis.
	 *
	 * @return true if at boundary, false if not.
	 */
	public boolean isAtBoundary() {
		int max = scope.getMax();
		return i == 0 || i == max - 1 || j == 0 || j == max - 1;
	}

	/**
	 * Returns the shortest distance from a boundary, in index 0 -> max - 1. Therefore, the shortest distance to boundary of 1,7 if max = 8 would be 0. If max was 9, it would be 1.
	 *
	 * @return the shortest distance from a boundary
	 */
	public int shortestToBoundary() {
		int max = scope.getMax();
		int[] distances = new int[]{
				i, j,
				max - 1 - i,
				max - 1 - j};
		return getSmallest(distances);
	}

	/**
	 * Resets all indexes to 0.
	 */
	public void reset() {
		i = 0;
		j = 0;
	}

	public int getI() {
		return i;
	}

	public int getJ() {
		return j;
	}

	private Scope2D getScope() {
		return scope;
	}

	@Override
	public boolean equals(Object obj) {
		if (obj == this) return true;
		if (obj instanceof Position2D) {
			Position2D other = (Position2D) obj;
			return getI() == other.getI() && getJ() == other.getJ();
		} else return false;
	}

	/**
	 * Returns a hash code for this {@code Position3D} object.
	 *
	 * @return a hash code for this {@code Position3D} object.
	 */
	@Override
	public int hashCode() {
		if (hash == 0) {
			long bits = 7L;
			bits = 31L * bits + Double.doubleToLongBits(getI());
			bits = 31L * bits + Double.doubleToLongBits(getJ());
			hash = (int) (bits ^ (bits >> 32));
		}
		return hash;
	}

	@Override
	public String toString() {
		return "{i=" + i +
				", j=" + j +
				'}';
	}

	public String toCSV(){
		return i + "," + j;
	}
}
