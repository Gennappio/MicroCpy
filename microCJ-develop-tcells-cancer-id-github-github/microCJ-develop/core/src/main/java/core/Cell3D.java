package core;
/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */


import geom.Point;
import geom.threeDim.Point3D;
import update.UpdateCollector;

/**
 * Base class for Cell objects.
 * @author Pedro Victori
 */
public class Cell3D extends Cell implements Agent3D {
	private Point3D location;

	/**
	 *  Creates a cell with the specified parameters, without a location
	 * @param radius the radius of the new cell
	 * @param graphFile The file from which the Network will be imported.
	 * @param randomiseDecisionWindow Whether the start of the decision window should be random or not.
	 * @param updateCollector for detecting apoptosis or necrosis updates
	 */
	public Cell3D(double radius, String celltype, String graphFile, boolean randomiseDecisionWindow, UpdateCollector updateCollector, String cellid) {
		super(radius, celltype, graphFile,randomiseDecisionWindow, updateCollector, cellid);
	}

	/**
	 * Creates a cell with the specified parameters.
	 *
	 * @param location                a Point3D object representing the 3D coordinates of the new Cell's location.
	 * @param radius                  the radius of the new cell
	 * @param graphFile               The file from which the Network will be imported.
	 * @param randomiseDecisionWindow Whether the start of the decision window should be random or not.
	 * @param updateCollector         for detecting apoptosis or necrosis updates
	 */
	public Cell3D(Point3D location, double radius, String celltype, String graphFile, boolean randomiseDecisionWindow, UpdateCollector updateCollector, String cellid) {
		this(radius, celltype, graphFile, randomiseDecisionWindow, updateCollector, cellid);
		this.location = location;
	}


	@Override
	public Point3D getPoint3D() {
		return location;
	}

	@Override
	public Point getLocation() {
		return getPoint3D();
	}

	@Override
	public void setLocation(Point3D location) {
		this.location = location;
	}


	public Cell createCopy() {
		return new Cell3D(radius, celltype, graphFile, true,updateCollector, cellid);
	}

	@Override
	public boolean is3D() {
		return true;
	}
}