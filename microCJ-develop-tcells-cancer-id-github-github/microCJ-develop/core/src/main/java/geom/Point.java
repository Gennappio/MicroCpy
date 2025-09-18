package geom;

public interface Point {
	double getX();

	double getY();

	/**
	 * @return a String representing the object in a final user presentation format.
	 */
	String toUserString();
}
