package diffusion.utils.threeDim;

import diffusion.utils.ElementProvider;

public interface GrowableMatrix<E> extends Iterable<E> {
	/**
	 * Makes the matrix larger, by adding the specified number of elements to the outermost layer in all directions. So a i,j,z matrix (i=j=z) would be transformed into a 1+i+1, 1+j+1, 1+z+1 matrix.
	 *
	 * @param growth          number of elements to be added to each side.
	 * @param elementProvider an ElementProvider that will be used to create the new elements.
	 */
	void grow(int growth, ElementProvider<E> elementProvider);
}
