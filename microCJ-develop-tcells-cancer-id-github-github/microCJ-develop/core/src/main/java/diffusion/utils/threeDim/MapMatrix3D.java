package diffusion.utils.threeDim;

import diffusion.utils.ElementProvider;

import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * Implementation of {@code Matrix3D} that stores the matrix as a {@code Map<Position3D, E>}
 *
 * @param <E> The type of the elements inside this matrix
 */
public class MapMatrix3D<E> implements Matrix3D<E> {
	private final Map<Position3D, E> matrix = new HashMap<>();
	private Scope scope;

	/**
	 * Creates a populated instance of a Matrix3D. The list of elements needs to be of the exact size required to fill a Matrix of dimensions xyz where x = y = z. In other words, its cube root must be an integer.
	 *
	 * @param elements the list of elements that will be used to populate the Matrix
	 */
	public MapMatrix3D(List<E> elements) {
		double cubicRoot = Math.cbrt(elements.size());
		if (cubicRoot == Math.floor(cubicRoot)) { //checks if the cube root is an integer and therefore the list has the adequate number of elements
			scope = new Scope((int) cubicRoot);
		} else throw new IllegalArgumentException("Invalid list size");

		Iterator<E> it = elements.iterator();

		for (Position3D position3D : scope) {
			matrix.put(position3D, it.next());
		}
	}

	public MapMatrix3D(ElementProvider<E> provider, int max){
		this.scope = new Scope(max);
		for (Position3D position3D : scope) {
			matrix.put(position3D, provider.buildElement());
		}
	}

	@Override
	public E get(Position3D pos) {
		return matrix.get(pos);
	}

	@Override
	public E get(int i, int j, int k) {
		return get(new Position3D(i, j, k, scope));
	}

	@Override
	public E set(Position3D pos, E element) {
		return matrix.put(pos, element);
	}

	@Override
	public E set(int i, int j, int k, E element) {
		return set(new Position3D(i, j, k, scope), element);
	}

	@Override
	public Scope getScope() {
		return scope;
	}

	@Override
	public void grow(int growth, ElementProvider<E> elementProvider) {
		Map<Position3D, E> newMatrix = new HashMap<>();
		Scope newScope = new Scope(getScope().getMax() + growth);
		for (Position3D position3D : newScope) {
			if (position3D.shortestToBoundary() < growth) { //if this should be a new element
				newMatrix.put(position3D, elementProvider.buildElement());
			} else {
				newMatrix.put(position3D, get(position3D.getI() - growth,
						position3D.getJ() - growth,
						position3D.getK() - growth));
			}
		}

		matrix.clear();
		matrix.putAll(newMatrix);
		scope = newScope;
	}
}
