/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package diffusion.utils.threeDim;

public class Position3D{
	private int i;
	private int j;
	private int k;
	private final Scope scope;

	/**
	 * Cache the hash code to make computing hashes faster.
	 */
	private int hash = 0;

	Position3D(int i, int j, int k, Scope scope) {
		this.i = i;
		this.j = j;
		this.k = k;
		this.scope = scope;
	}

	Position3D(Position3D pos) {
		this.i = pos.i;
		this.j = pos.j;
		this.k = pos.k;
		this.hash = pos.hash;
		this.scope = pos.getScope();
	}

	void increment() {
		k++;
		int max = scope.getMax();
		if (k == max) {
			k = 0;
			j++;
			if (j == max) {
				j = 0;
				i++;
				if (i > max) {
					throw new IndexOutOfBoundsException();
				}
			}
		}
		hash = 0; //cause hash to be recomputed after modification
	}

	boolean isAtMax() {
		int max = scope.getMax();
		return i >= max;
	}

	/**
	 * Whether the current position is at the boundaries of the 3D matrix, that is, at 0 or at the maximum value in any axis.
	 * @return true if at boundary, false if not.
	 */
	public boolean isAtBoundary() {
		int max = scope.getMax();
		return i == 0 || i == max-1 || j == 0 || j == max-1 || k == 0 || k == max-1;
	}

	/**
	 * Returns the shortest distance from a boundary, in index 0 -> max - 1. Therefore, the shortest distance to boundary of 1,5,7 if max = 8 would be 0. If max was 9, it would be 1.
	 * @return the shortest distance from a boundary
	 */
	public int shortestToBoundary(){
		int max = scope.getMax();
		int[] distances = new int[]{
				i, j, k,
				max - 1 - i,
				max - 1 - j,
				max - 1 - k};
		return getSmallest(distances);
	}

	/**
	 * Resets all indexes to 0.
	 */
	public void reset() {
		i = 0;
		j = 0;
		k = 0;
	}

	public int getI() {
		return i;
	}

	public int getJ() {
		return j;
	}

	public int getK() {
		return k;
	}

	private Scope getScope() {
		return scope;
	}

	@Override
	public boolean equals(Object obj) {
		if (obj == this) return true;
		if (obj instanceof Position3D) {
			Position3D other = (Position3D) obj;
			return getI() == other.getI() && getJ() == other.getJ() && getK() == other.getK();
		} else return false;
	}

	/**
	 * Returns a hash code for this {@code Position3D} object.
	 * @return a hash code for this {@code Position3D} object.
	 */
	@Override public int hashCode() {
		if (hash == 0) {
			long bits = 7L;
			bits = 31L * bits + Double.doubleToLongBits(getI());
			bits = 31L * bits + Double.doubleToLongBits(getJ());
			bits = 31L * bits + Double.doubleToLongBits(getK());
			hash = (int) (bits ^ (bits >> 32));
		}
		return hash;
	}

	@Override
	public String toString() {
		return "{i=" + i +
				", j=" + j +
				", k=" + k +
				'}';
	}

	public String toCSV(){
		return i + "," + j + "," + k;
	}

	private int getSmallest(int[] numbers){
		int smallest = numbers[0];
		for (int number : numbers) {
			if(number < smallest) smallest = number;
		}
		return smallest;
	}
}
