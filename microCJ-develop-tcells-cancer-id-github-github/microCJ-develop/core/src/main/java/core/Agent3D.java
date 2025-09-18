package core;

import geom.threeDim.Point3D;

public interface Agent3D extends Agent{
	/**
	 * Returns the location of the agent within the World limits
	 * @return a Point3D representing the 3D coordinates of the agent's location
	 */
	Point3D getPoint3D();

	/**
	 * Moves the agent to a new location.
	 * @param location A Point3D object representing the 3D coordinates of the Agent's new location
	 */
	void setLocation(Point3D location);
}
