package diffusion.utils;

import diffusion.utils.threeDim.*;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Collections;
import java.util.List;
import java.util.Random;
import java.util.stream.Collectors;

public class Test {

	private static List<Position3D> positions;

	public static void main(String[] args) {
		int max = 200;
		Scope scope = new Scope(max);
		positions = scope.stream().collect(Collectors.toList());
		Collections.shuffle(positions);//for later testing

		ElementProvider<String> stringProvider = () -> { //random string
			byte[] array = new byte[3];
			new Random().nextBytes(array);
			return new String(array, StandardCharsets.UTF_8);
		};

		Instant start = Instant.now();
		MapMatrix3D<String> mapMatrix = new MapMatrix3D<>(stringProvider, max);
		Instant end = Instant.now();
		long mapCreation = Duration.between(start, end).toMillis();

		start = Instant.now();
		ArrayMatrix3D<String> arrayMatrix = new ArrayMatrix3D<>(stringProvider, max);
		end = Instant.now();
		long arrayCreation = Duration.between(start, end).toMillis();

		start = Instant.now();
		test(mapMatrix);
		end = Instant.now();
		long mapTest = Duration.between(start, end).toMillis();

		start = Instant.now();
		test(arrayMatrix);
		end = Instant.now();
		long arrayTest = Duration.between(start, end).toMillis();

		start = Instant.now();
		mapMatrix.grow(50, stringProvider);
		test(mapMatrix);
		end = Instant.now();
		long mapGrowTest = Duration.between(start, end).toMillis();

		start = Instant.now();
		arrayMatrix.grow(50, stringProvider);
		test(arrayMatrix);
		end = Instant.now();
		long arrayGrowTest = Duration.between(start, end).toMillis();

		System.out.println("mapCreation = " + mapCreation);
		System.out.println("arrayCreation = " + arrayCreation);
		System.out.println("mapTest = " + mapTest);
		System.out.println("arrayTest = " + arrayTest);
		System.out.println("mapGrowTest = " + mapGrowTest);
		System.out.println("arrayGrowTest = " + arrayGrowTest);	}

	private static void test(Matrix3D<String> matrix){
		for (Position3D position : positions) {
			System.out.println(matrix.get(position));
		}
	}
}
