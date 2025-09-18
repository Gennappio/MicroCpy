module microCJ.core {
	exports graph;
	exports geom;
	exports geom.threeDim;
	exports geom.twoDim;
	exports core;
	exports update;
	exports utils;
	exports diffusion;
	exports diffusion.utils;
	exports diffusion.utils.threeDim;
	exports diffusion.utils.twoDim;
	exports stats;

	requires org.apache.commons.configuration2;
	requires java.sql;
	requires org.jgrapht.core;
	requires org.jgrapht.io;
	requires jbool.expressions;
	requires commons.csv;
	requires org.tinylog.api;
	requires zip4j;
}