package diffusion.utils.threeDim;

import diffusion.utils.ElementProvider;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

/**
 * Implementation of {@code Matrix3D} that stores the matrix as three {@code List} one inside another.
 *
 * @param <E> The type of the elements inside this matrix
 */
public class ArrayMatrix3D<E> implements Matrix3D<E> {
	private List<List<List<E>>> matrix;
	private Scope scope;

	/**
	 * Creates a populated instance of ArrayMatrix3D.
	 * The list of elements needs to be of the exact size required to fill a Matrix of dimensions xyz where x = y = z.
	 * In other words, its cube root must be an integer.
	 *
	 * @param elements the list of elements that will be used to populate the Matrix
	 */
	public ArrayMatrix3D(List<E> elements) {
		double cubicRoot = Math.cbrt(elements.size());
		int scopeSize;
		if (cubicRoot == Math.floor(cubicRoot)) { //checks if the cube root is an integer and therefore the list has the adequate number of elements
			scopeSize = (int) cubicRoot;
		} else throw new IllegalArgumentException("Invalid list size");
		scope = new Scope(scopeSize);
		matrix = new ArrayList<>(scopeSize);
		Iterator<E> it = elements.iterator();
		for (int i = 0; i < scopeSize; i++) {
			List<List<E>> arrayYZ = new ArrayList<>(scopeSize);
			for (int j = 0; j < scopeSize; j++) {
				List<E> arrayZ = new ArrayList<>(scopeSize);
				for (int k = 0; k < scopeSize; k++) {
					arrayZ.add(it.next());
				}
				arrayYZ.add(arrayZ);
			}
			matrix.add(arrayYZ);
		}
	}

	/**
	 * Creates a populated instance of ArrayMatrix3D with a give maximum size
	 * An {@code ElementProvider<E>} object is used to supply the required elements.
	 * @param provider an {@code ElementProvider<E>} able to supply the required number of elements.
	 * @param max the maximum size
	 */
	public ArrayMatrix3D(ElementProvider<E> provider, int max) {
		this.scope = new Scope(max);
		matrix = new ArrayList<>(max);
		for (int i = 0; i < max; i++) {
			List<List<E>> arrayYZ = new ArrayList<>(max);
			for (int j = 0; j < max; j++) {
				List<E> arrayZ = new ArrayList<>(max);
				for (int k = 0; k < max; k++) {
					arrayZ.add(provider.buildElement());
				}
				arrayYZ.add(arrayZ);
			}
			matrix.add(arrayYZ);
		}
	}

	@Override
	public E get(Position3D pos) {
		return get(pos.getI(), pos.getJ(), pos.getK());
	}

	@Override
	public E get(int i, int j, int k) {
		return matrix.get(i).get(j).get(k);
	}

	@Override
	public E set(Position3D pos, E element) {
		return set(pos.getI(), pos.getJ(), pos.getK(), element);
	}

	@Override
	public E set(int i, int j, int k, E element) {
		return matrix.get(i).get(j).set(k, element);
	}

	@Override
	public Scope getScope() {
		return scope;
	}

	@Override
	public void grow(int growth, ElementProvider<E> elementProvider) {
		//create a new matrix filled with new elements
		ArrayMatrix3D<E> newMatrix = new ArrayMatrix3D<>(elementProvider, getScope().getMax() + growth);

		for (Position3D position3D : newMatrix.scope) {
			/*check if this position is inside the original matrix, therefore it has to be replaced with an old
			element from the original matrix. Otherwise, do nothing, since a new element was already generated
			in the previous step.*/
			if(position3D.shortestToBoundary() >= growth) {
				newMatrix.set(position3D, get(position3D));
			}
		}
		matrix = newMatrix.matrix;
		scope = newMatrix.scope;
	}
}
