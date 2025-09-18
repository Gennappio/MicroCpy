package diffusion.utils;

@FunctionalInterface
public interface ElementProvider<E> {
	/**
	 * When called return an {@code E} instance, creating it if necessary.
	 * @return an {@code E} instance
	 */
	E buildElement();
}